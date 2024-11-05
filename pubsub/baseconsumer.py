import time
import os
import asyncio
from google.cloud import pubsub_v1
from concurrent.futures import TimeoutError
from concurrent.futures import ThreadPoolExecutor
import threading
import json
from utils.logger import logger
from db.client import db_client, StatusEnum
from datetime import datetime
from datetime import timezone

from config.conf import max_file_size, max_duration, message_timeout, conn_retry_interval, ack_deadline_seconds
from config.conf import facefusion_topic_name, facefusion_subscription_name, project_name, env_gcs_bucket_url, env_project_id, service, bucket_name, sub_path
from main2 import ModelSwapper
from alert import task_manager
import requests
import tempfile
import subprocess
import shutil
from bucket import gcs_utils


def convert_mp4(input_mp4, output_file, conversion_type, **kwargs):
    """
    通用的 MP4 转换函数。

    参数:
    - input_mp4: 输入的 MP4 文件路径。
    - output_file: 输出文件路径。
    - conversion_type: 转换类型 ('gif' 或 'webp')。
    - kwargs: 其他可选参数（如 fps, scale, quality 等）。

    返回:
    - None
    """
    if not os.path.exists(input_mp4):
        logger.error(f"Input file does not exist: {input_mp4}")
        return

    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        t0 = time.time()
        
        # 生成临时输出文件路径
        suffix = f".{conversion_type}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_output_file = temp_file.name

        if conversion_type == 'gif':
            # 改进的 GIF 转换命令
            cmd = [
                'ffmpeg', '-y',
                '-i', input_mp4,
                '-vf', 'fps=15,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
                '-loop', '0',
                temp_output_file
            ]
        elif conversion_type == 'webp':
            fps = kwargs.get('fps', 15)
            quality = kwargs.get('quality', 80)
            loop = kwargs.get('loop', 0)
            cmd = [
                'ffmpeg', '-y',
                '-i', input_mp4,
                '-vf', f'fps={fps}',
                '-vcodec', 'libwebp',
                '-lossless', '0',
                '-compression_level', '6',
                '-q:v', str(quality),
                '-loop', str(loop),
                temp_output_file
            ]
        else:
            logger.error(f"Unsupported conversion type: {conversion_type}")
            raise ValueError(f"Unsupported conversion type: {conversion_type}")

        logger.info(f"Converting MP4 {input_mp4} to {conversion_type.upper()}, output to {temp_output_file}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        if result.returncode == 0:
            shutil.move(temp_output_file, output_file)
            logger.info(f"MP4 converted and saved to {output_file}")
        else:
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        
        t1 = time.time()
        logger.info(f"MP4 to {conversion_type.upper()} conversion total time: {t1 - t0:.2f}s")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting MP4 to {conversion_type.upper()}: {e.stderr}", exc_info=True)
        if os.path.exists(temp_output_file):
            os.remove(temp_output_file)
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        if os.path.exists(temp_output_file):
            os.remove(temp_output_file)
        raise e

def generate_gcs_file_path(unique_id=None, extension=None):
    """
    生成GCS文件路径: mtask_storage/队列名/日期/任务id.文件后缀

    参数:
    - bucket_name: GCS存储桶名
    - topic_name: 队列名
    - unique_id: 任务id
    - extension: 文件后缀

    返回:
    - 完整的GCS文件路径
    """
    date_path = datetime.utcnow().strftime("%Y%m%d")
    return f"{sub_path}/{date_path}/{unique_id}{extension}"

class BaseConsumer:
    MAX_SIZE = max_file_size  # 500 MB in bytes
    MAX_DURATION = max_duration  # 10 minutes in seconds
    MESSAGE_TIMEOUT = message_timeout  # 1 hour in seconds
    CONN_RETRY_INTERVAL = conn_retry_interval  # 5 seconds

    def __init__(self, name, project_id=env_project_id, topic_name=facefusion_topic_name, subscription_name=facefusion_subscription_name, max_messages=1, max_lease_duration=MESSAGE_TIMEOUT):
        self.name = name
        self.project_id = project_id
        self.topic_name = topic_name
        self.subscription_name = subscription_name
        self.topic_path = f'projects/{self.project_id}/topics/{self.topic_name}'
        self.subscription_path = f'projects/{self.project_id}/subscriptions/{self.subscription_name}'
        self.subscriber = pubsub_v1.SubscriberClient()
        self.flow_control = pubsub_v1.types.FlowControl(
            max_messages=max_messages,
            max_lease_duration=max_lease_duration  # 设置最大租约持续时间为3600秒（1小时）
        )
        if self.MESSAGE_TIMEOUT < 100:
            self.timeout = 5  # 最小确认超时时间
        else:
            self.timeout = self.MESSAGE_TIMEOUT - 100  # 确认超时时间
        self.count = 0
        self.lock = threading.Lock()
        self.swapper = ModelSwapper()
        self.unacknowledged_messages = {}  # 存储未确认的消息

        logger.info(f"Consumer {self.name} initialized.")

    def add_count(self):
        with self.lock:
            self.count += 1

    def check_timeout(self, timeout_at):
        """
        检查任务是否过期
        
        :param timeout_at: 任务过期时间，格式为 "2024-10-28 07:26:24" (UTC 0时区) 字符串
        :return: True 如果任务未过期，否则抛出 TimeoutError
        :raises: TimeoutError 如果任务已过期
        """
        try:
            if timeout_at == '':
                raise ValueError("timeout_at is empty")
            
            # 将字符串转换为datetime对象（UTC时间）
            timeout_time = datetime.strptime(timeout_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            
            # 获取当前UTC时间
            current_time = datetime.now(timezone.utc)
            
            # 检查是否过期
            if current_time > timeout_time:
                raise TimeoutError(f"Task timeout at {timeout_at} UTC")
            
            # 计算剩余时间
            time_remaining = timeout_time - current_time
            total_seconds = time_remaining.days * 86400 + time_remaining.seconds
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            # 始终显示完整的时分秒
            logger.info(f"Task is valid: {hours:02d}:{minutes:02d}:{seconds:02d} remaining until timeout")
                
            return True
            
        except ValueError as e:
            # 处理日期格式错误
            raise ValueError(f"Invalid datetime format. Expected 'YYYY-MM-DD HH:MM:SS', got {timeout_at}")
        except Exception as e:
            # 处理其他可能的错误
            raise Exception(f"Error checking timeout: {str(e)}")
        

    def validate_message(self, message):
        try:
            if not message or message.data is None:
                logger.error("Invalid message format.")
                raise ValueError("Invalid message format.")
            
            msg = json.loads(message.data.decode('utf-8'))
            input_data = msg.get("input_data", {})

            if 'source_url' not in input_data:
                logger.error(f"Invalid message format. Exiting.")
                raise ValueError("Invalid message format.")

            if 'detect_id' not in input_data :
                logger.error(f"detect_id is missing. Exiting.")
                raise ValueError("detect_id is missing.")
            
            if "timeout_at" not in msg:
                logger.error(f"timeout_at is missing. Exiting.")
                raise ValueError("timeout_at is missing.")
            
            if "task_id" not in msg or msg.get("task_id", '') == '':
                logger.error(f"task_id is missing. Exiting.")
                raise ValueError("task_id is missing.")

            self.check_timeout(msg.get("timeout_at", ""))
            
            return input_data.get("detect_id", ''), input_data.get("source_url", ''), input_data.get("target_url", ''), msg.get("task_id", '')
        except Exception as e:
            logger.error(f"Error validating message: {e}", exc_info=True)
            raise e



    def download_file(self, url, file_name):
        """
        从URL下载文件到本地临时目录
        
        Args:
            url (str): 文件的URL地
            
        Returns:
            str: 下载文件的本地路径
        """
        try:
            # 创建临时文件
            temp_dir = 'temp'
            os.makedirs(temp_dir, exist_ok=True)
            
            # 生成临时文件名
            temp_path = os.path.join(temp_dir, file_name)
            
            # 下载文件
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # 检查文件大小
            content_length = len(response.content)
            if content_length > self.MAX_SIZE:
                raise ValueError(f"File size ({content_length} bytes) exceeds maximum allowed size ({self.MAX_SIZE} bytes)")
            
            # 保存文件
            with open(temp_path, 'wb') as f:
                f.write(response.content)
                
            logger.info(f"Successfully downloaded file to: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to download file from {url}: {str(e)}")
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def handle_task_info(self, detect_id, target_url):
        """
        处理任务信息，获取目标URL和媒体信息
        
        Args:
            detect_id (str): 检测任务ID
            target_url (str): 目标URL
            
        Returns:
            tuple: (target_url, media_type, width, height)
            
        Raises:
            ValueError: 当任务数据无效或缺失时
        """
        try:
            # 获取任务数据
            task_data = task_manager.get_task_result(detect_id)
            if not task_data:
                raise ValueError(f"Task not found for detect_id: {detect_id}")
                
            # 获取任务详情
            task = task_data.get('data')
            if not task:
                raise ValueError(f"Task data is empty for detect_id: {detect_id}")
                
            # 检查任务状态
            task_status = task.get('task_status', '').lower()
            if task_status != 'succeeded':
                raise ValueError(f"Task status is '{task_status}' (not succeeded) for detect_id: {detect_id}")
                
            # 获取输出数据
            output = task.get('output_data')
            if not output:
                raise ValueError(f"Output data is missing for detect_id: {detect_id}")
                
            # 获取输入URL
            input_data = task.get('input_data', {})
            input_url = input_data.get('url', '') 
            convert_url = output.get('convert_url', '')   

            if not target_url:
                if convert_url:
                    target_url = convert_url
                else:
                    target_url = input_url
            else:
                if (target_url != input_url) and (target_url != convert_url):
                    logger.warning(f"Target URL ({target_url}) differs from input URL ({input_url}) or convert URL ({convert_url})")
               
            # 获取媒体信息
            duration = output.get('duration', 0)
            media_type = output.get('media_type', '').lower()
            if not media_type:
                raise ValueError(f"Media type is missing for detect_id: {detect_id}")
            else:
                if media_type not in ['video', 'gif', 'image']:
                    raise ValueError(f"Media type is invalid for detect_id: {detect_id}")
                if media_type in ['video', 'gif']:
                    if duration <= 0:
                        raise ValueError(f"Duration is invalid for detect_id: {detect_id}")
                
            # 获取尺寸信息
            width = output.get('width')
            height = output.get('height')
           
            if not width or not height:
                raise ValueError(f"Dimensions (width: {width}, height: {height}) are invalid for detect_id: {detect_id}")
                
            logger.info(f"""Task info retrieved successfully:
                detect_id: {detect_id}
                target_url: {target_url}
                media_type: {media_type}
                dimensions: {width}x{height}
                duration: {duration}
            """)
                
            return target_url, media_type, width, height
            
        except Exception as e:
            logger.error(f"Error processing task info for detect_id {detect_id}: {str(e)}", exc_info=True)
            raise


    def get_file_name(self, tpe, task_id, width, height, media_type):
        if media_type.lower() in ['video', 'gif']:
            return f"/tmp/{tpe}-{task_id}-{width}x{height}.mp4"
        else:
            return f"/tmp/{tpe}-{task_id}-{width}x{height}.jpg"


    def get_extension(self, media_type):
        if media_type.lower() in ['video']:
            return '.mp4'
        elif media_type.lower() in ['gif']:
            return '.gif'
        else:
            return '.jpg'
    

    def process_task(self, task_id, detect_id, source_url, target_url, message_id):
        source_path = None
        target_path = None
        output_path = None
        output_url = None
        extension = None
        gif_output_path = None
        try:
            logger.info(f"Processing task: {task_id}, {detect_id}, {source_url}, {target_url}")
            target_url, media_type, width, height = self.handle_task_info(detect_id, target_url)
            source_path = self.get_file_name('source', task_id, width, height, media_type)
            target_path = self.get_file_name('target', task_id, width, height, media_type)
            output_path = self.get_file_name('output', task_id, width, height, media_type)
            
            source_path = self.download_file(source_url, source_path)
            target_path = self.download_file(target_url, target_path)

            # logger.info(f"------> Processing task: {task_id}, {detect_id}, {source_path}, {target_path}, {output_path}")

            # 处理文件的其他逻辑...
            self.swapper.process(
                sources=[source_path],
                target=target_path,
                output=output_path,
                resolution=f"{width}x{height}"
            )
            if os.path.exists(output_path) and os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
                if media_type.lower() in ['gif']:
                    gif_output_path = f"/tmp/{media_type}-{task_id}-{width}x{height}.gif"
                    convert_mp4(output_path, gif_output_path, "gif")
                # 上传到GCS
                extension = self.get_extension(media_type)
                gcs_path = generate_gcs_file_path(message_id, extension)
                if gif_output_path: 
                    f, url = gcs_utils.upload_file(gif_output_path, gcs_path)
                else:
                    f, url = gcs_utils.upload_file(output_path, gcs_path)
                if f:
                    return url
                else:
                    raise ValueError("Failed to upload image")
            else:
                logger.error(f"Result file not found or empty, path: {output_path}")
                raise ValueError("Result file not found or empty.")
        finally:
            # 清理临时文件
            temp_files = [source_path, target_path, output_path, gif_output_path]
            for path in temp_files:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                        logger.debug(f"Cleaned up temporary file: {path}")
                    except Exception as e:
                        logger.error(f"Failed to cleanup temporary file {path}: {e}")


    def callback(self, message):
        t0 = time.time()
        msg = None
        request_id = None
        acked = False
        task_id = None
        try:
            self.add_count()
            detect_id, source_url, target_url, task_id = self.validate_message(message)

            # 创建任务
            request_id = db_client.create_face_swap_request(
                detect_id=detect_id,
                source_map_info=json.dumps({
                    "source_url": source_url
                }),
                target_url=target_url
            )
            # if request_id is None:
            #     raise ValueError("Failed to start video face swap request")

            # 更新任务ID
            task_manager.update_task(
                task_id=task_id,
                task_status='running',
                started_at=datetime.now(timezone.utc)
            )

            # 将消息添加到未确认消息列表
            self.unacknowledged_messages[message.message_id] = message

            # 立即续约消息租约
            self.subscriber.modify_ack_deadline(
                subscription=self.subscription_path,
                ack_ids=[message.ack_id],
                ack_deadline_seconds=ack_deadline_seconds
            )
            logger.info(f"Lease renewed for message {message.message_id}.")

            # Update the database status
            self.update_request_status(
                request_id=request_id,
                status= StatusEnum.running
            )

            # url = self.process_message(msg, resolution)
            url = self.process_task(task_id, detect_id, source_url, target_url, message.message_id)

            # 只有在成功获取URL后才更新状态为成功
            if url:
                # 使用 ack_with_response() 进行消息确认
                ack_future = message.ack_with_response()
                ack_future.result(timeout=20)
                acked = True  # 标记消息已确认
                t1 = time.time()
                processing_time = round(t1 - t0, 2)
                
                # 更新成功态
                self.update_request_status(
                    request_id=request_id,
                    status=StatusEnum.succeeded,
                    processing_time=processing_time,
                    result_url=url
                )
                task_manager.update_task(
                    task_id=task_id,
                    task_status='succeeded',
                    finished_at=datetime.now(timezone.utc),
                    output_data={
                        "url": url
                    }
                )
                logger.info(f"Task completed successfully for message {message.message_id}")
            else:
                raise ValueError("Process task completed but no URL returned")

        except TimeoutError as e:
            logger.error(f"Timeout error for message {message.message_id}: {e}", exc_info=True)

            if task_id is not None:
                task_manager.update_task(
                    task_id=task_id,
                    task_status='timeout',
                    finished_at=datetime.now(timezone.utc),
                    task_message=str(e)
                )
            if request_id is not None:
                self.update_request_status(
                    request_id=request_id,
                    status=StatusEnum.timeout,
                    error_message=str(e),
                    processing_time=round(time.time() - t0, 2)
                )

        except Exception as e:
            logger.error(f"Error processing message {message.message_id}: {e}", exc_info=True)
            if task_id is not None:
                task_manager.update_task(
                    task_id=task_id,
                    task_status='failed',
                    finished_at=datetime.now(timezone.utc),
                    task_message=str(e)
                )
            if request_id is not None:
                self.update_request_status(
                    request_id=request_id,
                    status=StatusEnum.failed,
                    error_message=str(e),
                    processing_time=round(time.time() - t0, 2)
                )

        finally:
            try:
                # 确保消息被确认
                if not acked:
                    message.ack()
                # 从未确认消息列表中移除
                if message.message_id in self.unacknowledged_messages:
                    del self.unacknowledged_messages[message.message_id]
            except Exception as e:
                logger.error(f"Error in cleanup: {e}", exc_info=True)

    async def lease_management(self, stop_event):
        while not stop_event.is_set():
            try:
                await asyncio.sleep(ack_deadline_seconds / 2)  # 每隔 timeout/2 秒检查一次
                for message_id, message in self.unacknowledged_messages.items():
                    logger.info(f"Renewing lease for message {message_id}")
                    self.subscriber.modify_ack_deadline(
                        subscription=self.subscription_path,
                        ack_ids=[message.ack_id],
                        ack_deadline_seconds=ack_deadline_seconds / 2
                    )
            except Exception as e:
                logger.error(f"Error in lease management: {e}", exc_info=True)

    def start_consumer(self, stop_event):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        lease_task = loop.create_task(self.lease_management(stop_event))

        try:
            while not stop_event.is_set():
                try:
                    # 检查订阅者客户端是否关闭，如果是，则重新连接
                    if self.subscriber is None or self.subscriber.closed:
                        self.subscriber = pubsub_v1.SubscriberClient()
                        logger.info("Subscriber reconnected.")

                    # 订阅消息
                    future = self.subscriber.subscribe(self.subscription_path, self.callback, flow_control=self.flow_control)
                    logger.info(f"Listening for messages on {self.subscription_path}...")

                    # 等待消息处理结果
                    future.result()
                except Exception as e:
                    # 捕获异常并记录日志，然后重新建立连接
                    if not stop_event.is_set():
                        logger.error(f"An error occurred: {e}. Restarting subscription...", exc_info=True)
                        time.sleep(self.CONN_RETRY_INTERVAL)  # 等待一段时间再尝试重新连接，避免频繁重试
                    else:
                        # 停止事件已设置，关闭订阅者客户端
                        self.subscriber.close()
                        logger.info("Subscriber closed due to stop event.")
        finally:
            loop.run_until_complete(lease_task)
            loop.close()

    def shutdown(self):
        if self.subscriber is not None and not self.subscriber.closed:
            self.subscriber.close()

    def update_request_status(self, request_id, status, error_message='', result_url='', processing_time=0):
        db_client.update_face_swap_status(
            request_id=request_id,
            status=status,
            processing_time=processing_time,
            error_message=error_message,
            result_url=result_url
        )


if __name__ == '__main__':

    consumers = [BaseConsumer(f"consumer-{i}") for i in range(3)]
    stop_event = threading.Event()

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(consumer.start_consumer, stop_event) for consumer in consumers]

        try:
            for future in futures:
                future.result()
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt, Shutdown requested...exiting")
            stop_event.set()
        finally:
            # 确保所有消费者都能正确关闭
            for consumer in consumers:
                consumer.shutdown()
