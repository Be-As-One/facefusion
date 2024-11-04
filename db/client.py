import os
from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, MetaData, Table, SmallInteger, Float, Boolean, ForeignKey, Enum, Index, func, BigInteger
from sqlalchemy.exc import SQLAlchemyError
from utils.logger import logger
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import enum
from utils.snowflake import generator
from config.conf import mysql_db_url

Base = declarative_base()

metadata = MetaData()


class StatusEnum(enum.Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    unknown = "unknown"
    timeout = "timeout"

class VideoDetect(Base):
    __tablename__ = 'video_detect'
    
    id = Column(BigInteger, primary_key=True, comment='十进制雪花算法生成的唯一ID')
    request_url = Column(Text, comment='记录请求路径（格式如“https://aaa/bb”）')
    request_gcs_path = Column(Text, comment='记录请求路径（格式如“bucket_subpath/2024/05/16/aaa.jpg”）')
    all_face_url = Column(Text, comment='所有脸图片URL(https://storage.googleapis.com/bucket_name/subpath/2024/07/12/aaa_all_face.jpg)')
    face_positions = Column(Text, comment='人脸位置信息（json）')
    
    # 通用信息
    media_type = Column(String(20), comment='媒体类型（video, gif, image）')
    width = Column(Integer, comment='图片宽度（最大 1080）')
    height = Column(Integer, comment='图片高度（最大 1920）')
    file_size = Column(Integer, comment='文件大小（KB，向下取整）')
    
    # 视频特有信息
    video_codec_name = Column(String(50), comment='视频编码器名称: h264')
    video_codec_type = Column(String(50), comment='视频编码器类型: video')
    video_frame_rate = Column(Float, comment='视频帧率')
    video_duration = Column(Float, comment='视频时长（秒, 向下取整）')
    
    # GIF 特有信息
    gif_frame_count = Column(Integer, comment='GIF 帧数')
    gif_duration = Column(Float, comment='GIF 时长（秒，向下取整）')
    
    # 请求状态记录
    wait_time = Column(Float, comment='等待时间（秒）')
    status = Column(Enum(StatusEnum), nullable=False, comment='请求状态（pending -> running -> succeeded / failed / unknown / timeout）')
    processing_time = Column(Float, comment='处理时间（秒）同步更新')
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment='请求创建时间')
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment='请求更新时间')
    error_message = Column(Text, comment='错误信息')
    have_audio = Column(SmallInteger, comment='是否包含音频', default=1)
    contains_adult_only = Column(SmallInteger, comment='是否仅包含成人内容', default=1)
    source = Column(String(100), comment='来源', default='')
    task_id = Column(String(100), comment='任务id', default='')
    new_file_url = Column(Text, comment='新文件URL', default='')
    
    # 添加索引
    __table_args__ = (
        Index('idx_status', 'status'),
        Index('idx_created_at', 'created_at'),
    )

class VideoFaceSwap(Base):
    __tablename__ = 'video_face_swap'

    id = Column(BigInteger, primary_key=True, comment='十进制雪花算法生成的唯一ID')
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment='请求创建时间')
    result_url = Column(Text, comment='结果URL')
    status = Column(Enum(StatusEnum), nullable=False, comment='请求状态（pending -> running -> succeeded / failed / unknown / timeout）')
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment='请求更新时间')
    processing_time = Column(Float, comment='处理时间（秒）')
    error_message = Column(Text, comment='错误信息')

    # 添加索引
    __table_args__ = (
        Index('idx_status', 'status'),
        Index('idx_created_at', 'created_at'),
    )



class RequestsDatabase:
    def __init__(self):
        self.engine = create_engine(mysql_db_url, 
                                    pool_size=2, 
                                    max_overflow=5, 
                                    pool_recycle=180,
                                    pool_pre_ping=True
                                )
        self.Session = scoped_session(sessionmaker(bind=self.engine))

    def check_db_connection(self):
        try:
            with self.engine.connect() as conn:
                conn.execute(text('SELECT 1'))
                logger.info("Database connection is OK")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Error occurred while checking database connection: {e}")
            return False

    def create_video_detect_request(self, request_url: str, request_gcs_path = ''):
        with self.Session() as session:
            try:
                request = VideoDetect(
                                 id = generator.generate_id(),
                                 request_url=request_url,
                                 request_gcs_path=request_gcs_path, 
                                 all_face_url='', 
                                 face_positions='', 
                                 media_type='', 
                                 width=0, 
                                 height=0, 
                                 file_size=0, 
                                 video_codec_name='', 
                                 video_codec_type='', 
                                 video_frame_rate=0, 
                                 video_duration=0, 
                                 gif_frame_count=0, 
                                 gif_duration=0, 
                                 wait_time=0, 
                                 status="pending", 
                                 processing_time=0, 
                                 created_at=datetime.now(), 
                                 updated_at=datetime.now(), 
                                 error_message=''
                    )
                session.add(request)
                session.commit()
                # 返回请求ID
                return request.id
            except SQLAlchemyError as e:
                logger.error(f"Error occurred while creating Video Detect Request: {e}")
                raise e

    def update_video_detect_info(self, request_id: str, media_type: str, width: int, height: int, file_size: int, video_codec_name: str = '', video_codec_type: str = '', video_frame_rate: float = 0, video_duration: float = 0, gif_frame_count: int = 0, gif_duration: float = 0.0, request_gcs_path: str = ''):
        with self.Session() as session:
            try:
                session.query(VideoDetect).filter(VideoDetect.id == request_id).update({
                    "media_type": media_type,
                    "width": width,
                    "height": height,
                    "file_size": file_size,
                    "video_codec_name": video_codec_name,
                    "video_codec_type": video_codec_type,
                    "video_frame_rate": video_frame_rate,
                    "video_duration": video_duration,
                    "gif_frame_count": gif_frame_count,
                    "gif_duration": gif_duration,
                    "request_gcs_path": request_gcs_path
                })
                session.commit()
                logger.info(f"Video Detect request info updated for request ID: {request_id}")
            except SQLAlchemyError as e:
                logger.error(f"Error occurred while updating Video Detect Request info: {e}")
                raise e

    def update_video_detect_request_status(self, request_id: str, status: str, processing_time: float = 0, error_message: str ='',  all_face_url:str = '', face_positions: str = ''):

        with self.Session() as session:
            try:
                session.query(VideoDetect).filter(VideoDetect.id == request_id).update({
                    "status": status,
                    "updated_at": datetime.now(),
                    "processing_time": processing_time,
                    "error_message": error_message,
                    "all_face_url": all_face_url,
                    "face_positions": face_positions
                })
                session.commit()
                logger.info(f"Video Detect request status updated for request ID: {request_id}")
            except SQLAlchemyError as e:
                logger.error(f"Error occurred while updating Video Detect Request status: {e}")
                raise e

    def get_video_detect_request_by_id(self, request_id: str):
        with self.Session() as session:
            try:
                data = session.query(VideoDetect).filter(VideoDetect.id == request_id).first()
                if data:
                    return data.__dict__
                else:
                    logger.info(f"No Video Detect request found for request_id: {request_id}")
                    return None
            except SQLAlchemyError as e:
                logger.error(f"Error occurred while querying Video Detect Request: {e}")
                raise e

    def create_video_face_swap_request(self):
        with self.Session() as session:
            try:
                request = VideoFaceSwap(
                                 id = generator.generate_id(),
                                 created_at=datetime.now(), 
                                 result_url='', 
                                 status="pending", 
                                 updated_at=datetime.now(), 
                                 processing_time=0, 
                                 error_message=''
                    )
                session.add(request)
                session.commit()
                # 返回请求ID
                return request.id
            except SQLAlchemyError as e:
                logger.error(f"Error occurred while creating Video Face Swap Request: {e}")
                raise e

    def update_video_face_swap_request_status(self, request_id: str, status: str, processing_time: float, error_message: str, result_url: str):
        with self.Session() as session:
            try:
                session.query(VideoFaceSwap).filter(VideoFaceSwap.id == request_id).update({
                    "status": status,
                    "processing_time": processing_time,
                    "error_message": error_message,
                    "result_url": result_url
                })
                session.commit()
                logger.info(f"Video Face Swap request status updated for request ID: {request_id}")
            except SQLAlchemyError as e:
                logger.error(f"Error occurred while updating Video Face Swap Request status: {e}")
                raise e

    def get_video_face_swap_request_by_id(self, request_id: str):
        with self.Session() as session:
            try:
                data = session.query(VideoFaceSwap).filter(VideoFaceSwap.id == request_id).first()
                if data:
                    return data.__dict__
                else:
                    logger.info(f"No Video Face Swap request found for request_id: {request_id}")
                    return None
            except SQLAlchemyError as e:
                logger.error(f"Error occurred while querying Video Face Swap Request: {e}")
                raise e

# 创建数据库连接
# requests_DB_client = RequestsDatabase()




if __name__ == '__main__':
    import time
    # id = requests_DB_client.create_video_detect_request("https://storage.googleapis.com/aipic-test/2024/07/12/aaa.mp4")
    # print("--->", id)
    # id = requests_DB_client.create_video_detect_request("https://storage.googleapis.com/aipic-test/2024/07/12/aaa.mp4", "bucket_subpath/2024/05/16/aaa.mp4")
    # print("--->", id)
    # time.sleep(6)
    # requests_DB_client.update_video_detect_info(id, "video", 1920, 1080, 1024, "h264", "video", 30, 60)
    # time.sleep(6)
    # requests_DB_client.update_video_detect_request_status(id, "running", 0, "", "", "", "")
    # data = requests_DB_client.get_video_detect_request_by_id(id)
    # print(data["id"], data["video_codec_name"])

    # id = requests_DB_client.create_video_face_swap_request()
    # print("--->", id)
    # time.sleep(6)
    # requests_DB_client.update_video_face_swap_request_status(id, "running", 0, "", "https://storage.googleapis.com/aipic-test/2024/07/12/aaa_output.mp4")
    # requests_DB_client.update_video_face_swap_request_status(id, "succeeded", 0, "", "https://storage.googleapis.com/aipic-test/2024/07/12/aaa_output.mp4")
    # data = requests_DB_client.get_video_face_swap_request_by_id(id)
    # print(data)

