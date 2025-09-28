"""
本地文件系统存储提供商
"""
import os
import logging
from pathlib import Path
from ..base import StorageProvider


logger = logging.getLogger(__name__)


class LocalProvider(StorageProvider):
    """本地文件系统存储提供商"""

    def __init__(self, base_path: str = "/workspace/results"):
        """
        初始化本地存储提供商
        
        Args:
            base_path: 本地存储的基础路径
        """
        self.base_path = Path(base_path)
        
        # 确保目录存在
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"本地存储路径已准备: {self.base_path}")
        except Exception as e:
            logger.error(f"创建本地存储目录失败: {e}")
            raise

    def upload_file(self, source_file_name: str, destination_path: str) -> str:
        """复制文件到本地存储目录"""
        try:
            source_path = Path(source_file_name)
            dest_path = self.base_path / destination_path
            
            # 确保目标目录存在
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 复制文件
            import shutil
            shutil.copy2(source_path, dest_path)
            
            logger.info(f"文件已复制到本地存储: {source_file_name} -> {dest_path}")
            
            # 删除源文件（如果是临时文件）
            if source_path.exists() and str(source_path).startswith('/tmp'):
                source_path.unlink()
                logger.debug(f"临时源文件已删除: {source_file_name}")
            
            return str(dest_path)
            
        except Exception as e:
            logger.error(f"本地文件复制失败: {e}")
            raise

    def upload_binary(self, binary_data: bytes, destination_path: str) -> str:
        """保存二进制数据到本地文件"""
        try:
            dest_path = self.base_path / destination_path
            
            # 确保目标目录存在
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(dest_path, 'wb') as f:
                f.write(binary_data)
            
            logger.info(f"二进制数据已保存到本地: {dest_path} ({len(binary_data)} bytes)")
            return str(dest_path)
            
        except Exception as e:
            logger.error(f"本地文件写入失败: {e}")
            raise

    def upload_base64(self, base64_data: str, destination_path: str) -> str:
        """保存base64数据到本地文件"""
        try:
            import base64
            
            # 处理 data URL 格式
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            
            # 解码并保存
            binary_data = base64.b64decode(base64_data)
            return self.upload_binary(binary_data, destination_path)
            
        except Exception as e:
            logger.error(f"Base64数据保存失败: {e}")
            raise

    def get_file_info(self, file_path: str) -> dict:
        """获取文件信息（扩展功能）"""
        try:
            full_path = self.base_path / file_path
            if not full_path.exists():
                return None
                
            stat = full_path.stat()
            return {
                "path": str(full_path),
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "exists": True
            }
        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return None

    def cleanup_old_files(self, days: int = 7) -> int:
        """清理指定天数前的文件（扩展功能）"""
        try:
            import time
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            deleted_count = 0
            
            for file_path in self.base_path.rglob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"已删除过期文件: {file_path}")
                    except Exception as e:
                        logger.warning(f"删除文件失败 {file_path}: {e}")
            
            logger.info(f"清理完成，删除了 {deleted_count} 个过期文件")
            return deleted_count
            
        except Exception as e:
            logger.error(f"文件清理失败: {e}")
            return 0