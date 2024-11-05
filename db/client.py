import os
from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, MetaData, SmallInteger, Float,  Enum, Index, func, BigInteger, SmallInteger
from sqlalchemy.exc import SQLAlchemyError
from utils.logger import logger
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timedelta
import enum
from utils.snowflake import generator
from config.conf import mysql_db_url

"""
-- 创建文件检测表
CREATE TABLE `filedetecter` (
    `id` BIGINT NOT NULL COMMENT '十进制雪花算法生成的唯一ID',
    `convert_url` TEXT COMMENT '新文件URL',
    `request_url` TEXT COMMENT '记录请求路径（格式如"https://aaa/bb"）',
    `all_face_url` TEXT COMMENT '所有脸图片URL(https://storage.googleapis.com/bucket_name/subpath/2024/07/12/aaa_all_face.jpg)',
    `face_positions` TEXT COMMENT '人脸位置信息（json）',
    
    -- 通用信息
    `media_type` VARCHAR(20) COMMENT '媒体类型（video, gif, image）',
    `width` INT COMMENT '图片宽度（最大 1080）',
    `height` INT COMMENT '图片高度（最大 1920）',
    `file_size` INT COMMENT '文件大小（KB，向下取整）',
    `codec_name` VARCHAR(50) COMMENT '视频编码器名称: h264',
    `duration` FLOAT COMMENT '时长（秒, 向下取整）',
    `have_audio` SMALLINT DEFAULT 1 COMMENT '是否包含音频',
    
    -- 请求状态记录
    `status` ENUM('pending', 'running', 'succeeded', 'failed', 'unknown', 'timeout') NOT NULL COMMENT '请求状态',
    `processing_time` FLOAT COMMENT '处理时间（秒）同步更新',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '请求创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '请求更新时间',
    `error_message` TEXT COMMENT '错误信息',
    `source` VARCHAR(100) DEFAULT '' COMMENT '来源',
    
    PRIMARY KEY (`id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件检测表';

-- 创建人脸替换表
CREATE TABLE `faceswapper` (
    `id` BIGINT NOT NULL COMMENT '十进制雪花算法生成的唯一ID',
    `detect_id` BIGINT COMMENT '视频检测ID',
    `source_map_info` TEXT COMMENT '源图像URL列表',
    `target_url` TEXT COMMENT '目标图像URL',
    `result_url` TEXT COMMENT '结果URL',
    `status` ENUM('pending', 'running', 'succeeded', 'failed', 'unknown', 'timeout') NOT NULL COMMENT '请求状态',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '请求创建时间',
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '请求更新时间',
    `processing_time` FLOAT COMMENT '处理时间（秒）',
    `error_message` TEXT COMMENT '错误信息',
    
    PRIMARY KEY (`id`),
    INDEX `idx_status` (`status`),
    INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='人脸替换表';
"""

Base = declarative_base()

metadata = MetaData()

class StatusEnum(enum.Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    unknown = "unknown"
    timeout = "timeout"

class FileDetector(Base):
    __tablename__ = 'filedetecter'
    
    id = Column(BigInteger, primary_key=True, comment='十进制雪花算法生成的唯一ID')
    convert_url = Column(Text, comment='新文件URL', default='')
    request_url = Column(Text, comment='记录请求路径（格式如"https://aaa/bb"）')
    all_face_url = Column(Text, comment='所有脸图片URL(https://storage.googleapis.com/bucket_name/subpath/2024/07/12/aaa_all_face.jpg)')
    face_positions = Column(Text, comment='人脸位置信息（json）')
    
    # 通用信息
    media_type = Column(String(20), comment='媒体类型（video, gif, image）')
    width = Column(Integer, comment='图片宽度（最大 1080）')
    height = Column(Integer, comment='图片高度（最大 1920）')
    file_size = Column(Integer, comment='文件大小（KB，向下取整）')
    codec_name = Column(String(50), comment='视频编码器名称: h264')
    duration = Column(Float, comment='时长（秒, 向下取整）')
    have_audio = Column(SmallInteger, comment='是否包含音频', default=1)

    # 请求状态记录
    status = Column(Enum(StatusEnum), nullable=False, comment='请求状态（pending -> running -> succeeded / failed / unknown / timeout）')
    processing_time = Column(Float, comment='处理时间（秒）同步更新')
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment='请求创建时间')
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment='请求更新时间')
    error_message = Column(Text, comment='错误信息')
    source = Column(String(100), comment='来源', default='')
    
    # 添加索引
    __table_args__ = (
        Index('idx_status', 'status'),
        Index('idx_created_at', 'created_at'),
    )

class FaceSwapper(Base):
    __tablename__ = 'faceswapper'

    id = Column(BigInteger, primary_key=True, comment='十进制雪花算法生成的唯一ID')
    detect_id = Column(BigInteger, comment='视频检测ID')
    source_map_info = Column(Text, comment='源图像URL列表')
    target_url = Column(Text, comment='目标图像URL')
    result_url = Column(Text, comment='结果URL')
    status = Column(Enum(StatusEnum), nullable=False, comment='请求状态（pending -> running -> succeeded / failed / unknown / timeout）')
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment='请求创建时间')
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

    def create_file_detect_request(self, request_url: str, source: str = '', id=None):
        """
        创建文件检测请求
        
        Args:
            request_url: 请求URL
            source: 来源
            id: 可选的ID（如果不提供则自动生成）
        
        Returns:
            int: 请求ID
        """
        with self.Session() as session:
            try:
                request = FileDetector(
                    id = id if id else generator.generate_id(),
                    request_url=request_url,
                    convert_url='',
                    all_face_url='',
                    face_positions='',
                    media_type='',
                    width=0,
                    height=0,
                    file_size=0,
                    codec_name='',
                    duration=0,
                    status=StatusEnum.pending,
                    processing_time=0,
                    error_message='',
                    source=source,
                    have_audio=1
                )
                session.add(request)
                session.commit()
                return request.id
            except SQLAlchemyError as e:
                logger.error(f"Error creating File Detect Request: {e}")
                raise e

    def update_file_detect_info(self, request_id: int, 
                              media_type: str, 
                              width: int, 
                              height: int, 
                              file_size: int, 
                              codec_name: str = '', 
                              duration: float = 0, 
                              have_audio: int = 1,
                              convert_url: str = ''):
        """更新文件检测信息"""
        with self.Session() as session:
            try:
                session.query(FileDetector).filter(FileDetector.id == request_id).update({
                    "media_type": media_type,
                    "width": width,
                    "height": height,
                    "file_size": file_size,
                    "codec_name": codec_name,
                    "duration": duration,
                    "have_audio": have_audio,
                    "convert_url": convert_url
                })
                session.commit()
                logger.info(f"File detect info updated for request ID: {request_id}")
            except SQLAlchemyError as e:
                logger.error(f"Error updating File Detect info: {e}")
                raise e

    def update_file_detect_status(self, request_id: int, 
                                status: StatusEnum, 
                                processing_time: float = 0, 
                                error_message: str = '',
                                all_face_url: str = '',
                                face_positions: str = ''):
        """更新文件检测状态"""
        with self.Session() as session:
            try:
                session.query(FileDetector).filter(FileDetector.id == request_id).update({
                    "status": status,
                    "processing_time": processing_time,
                    "error_message": error_message,
                    "all_face_url": all_face_url,
                    "face_positions": face_positions,
                    "updated_at": datetime.now()
                })
                session.commit()
                logger.info(f"File detect status updated for request ID: {request_id}")
            except SQLAlchemyError as e:
                logger.error(f"Error updating File Detect status: {e}")
                raise e

    def get_file_detect_request_by_id(self, request_id: str):
        """通过ID获取文件检测请求信息"""
        with self.Session() as session:
            try:
                data = session.query(FileDetector).filter(FileDetector.id == request_id).first()
                if data:
                    data_dict = {}
                    for column in data.__table__.columns:
                        value = getattr(data, column.name)
                        # 处理datetime类型
                        if isinstance(value, datetime):
                            value = value.strftime('%Y-%m-%d %H:%M:%S')
                        # 处理Enum类型
                        elif isinstance(value, StatusEnum):
                            value = value.value
                        data_dict[column.name] = value
                    return data_dict
                else:
                    logger.info(f"No File Detect request found for request_id: {request_id}")
                    return None
            except SQLAlchemyError as e:
                logger.error(f"Error querying File Detect Request: {e}")
                raise e

    def create_face_swap_request(self, detect_id: int, source_map_info: str, target_url: str):
        """
        创建人脸替换请求
        
        Args:
            detect_id: 视频检测ID
            source_map_info: 源图像URL列表（JSON字符串）
            target_url: 目标图像URL
            
        Returns:
            int: 请求ID
        """
        with self.Session() as session:
            try:
                request = FaceSwapper(
                    id=generator.generate_id(),
                    detect_id=detect_id,
                    source_map_info=source_map_info,
                    target_url=target_url,
                    result_url='',
                    status=StatusEnum.pending,
                    processing_time=0,
                    error_message=''
                )
                session.add(request)
                session.commit()
                return request.id
            except SQLAlchemyError as e:
                logger.error(f"Error creating Face Swap Request: {e}")
                raise e

    def update_face_swap_status(self, request_id: int, 
                              status: StatusEnum, 
                              processing_time: float = 0,
                              error_message: str = '',
                              result_url: str = ''):
        """
        更新人脸替换状态
        
        Args:
            request_id: 请求ID
            status: 状态
            processing_time: 处理时间（秒）
            error_message: 错误信息
            result_url: 结果URL
        """
        with self.Session() as session:
            try:
                session.query(FaceSwapper).filter(FaceSwapper.id == request_id).update({
                    "status": status,
                    "processing_time": processing_time,
                    "error_message": error_message,
                    "result_url": result_url,
                    "updated_at": datetime.now()
                })
                session.commit()
                logger.info(f"Face swap status updated for request ID: {request_id}")
            except SQLAlchemyError as e:
                logger.error(f"Error updating Face Swap status: {e}")
                raise e

    def get_face_swap_request_by_id(self, request_id: str):
        """通过ID获取人脸替换请求信息"""
        with self.Session() as session:
            try:
                data = session.query(FaceSwapper).filter(FaceSwapper.id == request_id).first()
                if data:
                    data_dict = {}
                    for column in data.__table__.columns:
                        value = getattr(data, column.name)
                        # 处理datetime类型
                        if isinstance(value, datetime):
                            value = value.strftime('%Y-%m-%d %H:%M:%S')
                        # 处理Enum类型
                        elif isinstance(value, StatusEnum):
                            value = value.value
                        data_dict[column.name] = value
                    return data_dict
                else:
                    logger.info(f"No Face Swap request found for request_id: {request_id}")
                    return None
            except SQLAlchemyError as e:
                logger.error(f"Error querying Face Swap Request: {e}")
                raise e

# 创建数据库连接
db_client = RequestsDatabase()


if __name__ == '__main__':
    import json
    import time
    
    # 创建数据库连接实例
    db = db_client
    
    def test_file_detect():
        """测试文件检测流程"""
        print("\n=== 测试文件检测流程 ===")
        try:
            # 1. 创建检测请求
            request_url = "https://storage.googleapis.com/for_test_file/test.mp4"
            detect_id = db.create_file_detect_request(request_url=request_url, source='test')
            print(f"创建检测请求成功，ID: {detect_id}")
            
            # 2. 更新文件信息
            db.update_file_detect_info(
                request_id=detect_id,
                media_type="video",
                width=1920,
                height=1080,
                file_size=1024,
                codec_name="h264",
                duration=60.0,
                have_audio=1,
                convert_url="https://storage.googleapis.com/converted/test.mp4"
            )
            print("更新文件信息成功")
            
            # 3. 更新检测状态和人脸信息
            face_positions = [
                {
                    "id": 1,
                    "x": 100,
                    "y": 100,
                    "width": 200,
                    "height": 200,
                    "quality_score": 0.95
                }
            ]
            
            db.update_file_detect_status(
                request_id=detect_id,
                status=StatusEnum.succeeded,
                processing_time=5.5,
                all_face_url="https://storage.googleapis.com/faces/test.jpg",
                face_positions=json.dumps(face_positions)
            )
            print("更新检测状态成功")
            
            # 4. 获取并验证结果
            result = db.get_file_detect_request_by_id(detect_id)
            print("\n检测请求最终状态:")
            print(json.dumps(result, indent=2))
            
            return detect_id
            
        except Exception as e:
            print(f"测试失败: {str(e)}")
            raise
    
    def test_face_swap():
        """测试人脸替换流程"""
        print("\n=== 测试人脸替换流程 ===")
        try:
            # 1. 首先创建一个检测请求（或使用已有的）
            detect_id = test_file_detect()
            
            # 2. 创建人脸替换请求
            source_map_info = json.dumps({
                "source_image_list": [
                    "https://storage.googleapis.com/source_faces/face1.jpg",
                    "https://storage.googleapis.com/source_faces/face2.jpg"
                ],
                "source_face_id_list": [[1, 2]]
            })
            
            swap_id = db.create_face_swap_request(
                detect_id=detect_id,
                source_map_info=source_map_info,
                target_url="https://storage.googleapis.com/targets/video.mp4"
            )
            print(f"创建替换请求成功，ID: {swap_id}")
            
            # 3. 更新替换状态
            time.sleep(1)  # 模拟处理时间
            db.update_face_swap_status(
                request_id=swap_id,
                status=StatusEnum.succeeded,
                processing_time=10.5,
                result_url="https://storage.googleapis.com/results/swapped.mp4"
            )
            print("更新替换状态成功")
            
            # 4. 获取并验证结果
            result = db.get_face_swap_request_by_id(swap_id)
            print("\n替换请求最终状态:")
            print(json.dumps(result, indent=2))
            
        except Exception as e:
            print(f"测试失败: {str(e)}")
            raise
    
    # 运行测试
    try:
        test_face_swap()  # 这会同时测试文件检测和人脸替换
        print("\n所有测试通过!")
    except Exception as e:
        print(f"\n测试过程中出现错误: {str(e)}")