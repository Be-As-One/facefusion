import requests
import json
from datetime import datetime
from utils.logger import logger
import argparse
import time  # 添加 time 模块的导入
from config.conf import base_url

class TaskManager:
    def __init__(self):
        self.base_url = base_url

    def _is_server_error(self, status_code):
        """
        判断是否为服务器错误(5xx)
        """
        return 500 <= status_code < 600

    def create_task(self, client_id, service, module, input_data):
        """
        创建新任务，遇到5xx错误时重试一次
        """
        url = f"{self.base_url}/task_create"
        
        payload = {
            "client_id": client_id,
            "service": service,
            "module": module,
            "input_data": input_data
        }

        for attempt in range(2):  # 最多尝试2次（初始 + 1次重试）
            try:
                response = requests.post(url, json=payload)
                if self._is_server_error(response.status_code) and attempt == 0:
                    logger.warning(f"Server error (5xx) on attempt {attempt + 1}, retrying...")
                    time.sleep(1)  # 重试前等待1秒
                    continue
                    
                response.raise_for_status()
                
                task_data = response.json()
                response_data = task_data.get('data')
                task_id = response_data.get('task_id')
                
                if task_id:
                    logger.info(f"Task created successfully with ID: {task_id}")
                    return task_id
                else:
                    logger.error("Task creation response did not include task_id")
                    return None
                    
            except requests.RequestException as e:
                if attempt == 1 or not self._is_server_error(getattr(e.response, 'status_code', 0)):
                    logger.error(f"Failed to create task: {str(e)}")
                    return None
                logger.warning(f"Server error on attempt {attempt + 1}, retrying...")
                time.sleep(1)

    def update_task(self, task_id, task_status, task_message=None, started_at=None, finished_at=None, output_data=None):
        """
        更新任务状态，遇到5xx错误时重试一次
        """
        url = f"{self.base_url}/task_update/{task_id}"
        
        payload = {
            "task_status": task_status
        }
        
        if task_message:
            payload["task_message"] = task_message
        if started_at:
            payload["started_at"] = started_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(started_at, datetime) else started_at
        if finished_at:
            payload["finished_at"] = finished_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(finished_at, datetime) else finished_at
        if output_data:
            payload["output_data"] = output_data

        for attempt in range(2):  # 最多尝试2次（初始 + 1次重试）
            try:
                response = requests.post(url, json=payload)
                if self._is_server_error(response.status_code) and attempt == 0:
                    logger.warning(f"Server error (5xx) on attempt {attempt + 1}, retrying...")
                    time.sleep(1)
                    continue
                    
                response.raise_for_status()
                logger.info(f"Task update sent successfully for task {task_id}")
                return True
                
            except requests.RequestException as e:
                if attempt == 1 or not self._is_server_error(getattr(e.response, 'status_code', 0)):
                    logger.error(f"Failed to send task update for task {task_id}: {str(e)}")
                    return False
                logger.warning(f"Server error on attempt {attempt + 1}, retrying...")
                time.sleep(1)

    def process_task(self, client_id, service, module, input_data, process_func):
        """
        创建任务，执行处理函数，并更新任务状态

        :param client_id: 请求方来源
        :param service: 服务名
        :param module: 模块名
        :param input_data: 输入数据字典
        :param process_func: 处理函数，接受 input_data 作为参数，返回输出数据
        :return: 处理是否成功
        """
        task_id = self.create_task(client_id, service, module, input_data)
        if not task_id:
            logger.error(f"Failed to create task")
            return False

        logger.info(f"Task created successfully with ID: {task_id}")

        self.update_task(task_id, "running", module, started_at=datetime.now(), finished_at=datetime.now())

        try:
            output_data = process_func(input_data)
            self.update_task(task_id, "succeeded", module, finished_at=datetime.now(), output_data=output_data)
            # return True
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {str(e)}")
            self.update_task(task_id, "failed", module, finished_at=datetime.now(), output_data={"error": str(e)})
            return False

        # get task
        data = self.get_task_result(task_id)
        logger.info(f"Task data: {data}")
        

    def get_task_result(self, task_id):
        """
        获取任务信息，遇到5xx错误时重试一次
        """
        url = f"{self.base_url}/task_result/{task_id}"

        for attempt in range(2):  # 最多尝试2次（初始 + 1次重试）
            try:
                response = requests.get(url)
                if self._is_server_error(response.status_code) and attempt == 0:
                    logger.warning(f"Server error (5xx) on attempt {attempt + 1}, retrying...")
                    time.sleep(1)
                    continue
                    
                response.raise_for_status()
                
                task_data = response.json()
                logger.info(f"Task result retrieved successfully for task {task_id}")
                return task_data
                
            except requests.RequestException as e:
                if attempt == 1 or not self._is_server_error(getattr(e.response, 'status_code', 0)):
                    logger.error(f"Failed to get task result for task {task_id}: {str(e)}")
                    return None
                logger.warning(f"Server error on attempt {attempt + 1}, retrying...")
                time.sleep(1)


task_manager = TaskManager()

# 使用示例
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Task Management Tool')
    parser.add_argument('--task-id', type=str, help='Task ID to query')
    parser.add_argument('--action', type=str, choices=['create', 'query', 'test'], default='query',
                       help='Action to perform (create or query)')
    args = parser.parse_args()

    if args.action == 'query' and args.task_id:
        # 获取任务结果示例
        task_result = task_manager.get_task_result(args.task_id)
        if task_result:
            print(f"Task result for task {args.task_id}:")
            print(json.dumps(task_result, indent=2))
        else:
            print(f"Failed to retrieve task result for task {args.task_id}")
    elif args.action == 'create':
        # 创建任务示例
        client_id = "com.ai.photoeditor.fx"
        service = "video-faceswap"
        module = "video-faceswap"
        # current_time = int(time.time())
        # url = "https://storage.googleapis.com/for_test_file/image2video/2.png"
        # url = "https://storage.googleapis.com/for_test_file/baby.png"
        input_data = {
            "detect_id": "rdet:1858816913103122432",
            "source_url": "https://storage.googleapis.com/for_test_file/image2video/2.png",
            # "target_url": "https://storage.googleapis.com/for_test_file/video/target.mp4"
            "target_url": None
        }
        
        task_id = task_manager.create_task(client_id, service, module, input_data)
        if task_id:
            print(f"Task created successfully with resp: {task_id}")
        else:
            print("Failed to create task")
    elif args.action == 'test':
        # 创建任务示例
        client_id = "com.ai.photoeditor.fx"
        service = "video-faceswap"
        module = "video-faceswap"
        # current_time = int(time.time())
        # url = "https://storage.googleapis.com/for_test_file/image2video/2.png"
        # url = "https://storage.googleapis.com/for_test_file/baby.png"
        input_data = {
            "detect_id": "rdet:1858795455345848320",
            "source_url": "https://storage.googleapis.com/for_test_file/image2video/2.png",
            "target_url":  None
        }
        
        def run(data):
            print("----------------> input data:",  data)
        
        task_id = task_manager.process_task(client_id, service, module, input_data, run)
        if task_id:
            print(f"Task created successfully with resp: {task_id}")
        else:
            print("Failed to create task")
    else:
        parser.print_help()
 


# 查询任务结果
# python alert.py --task-id rvfs:1858817085455462400
# python alert.py --task-id rdet:1858813680095850496

# 创建新任务
# python alert.py --action create

#  python alert.py --action test

# git rm -r --cached .assets
# git commit -m "Remove directory '.assets' from git repository"