"""
存储管理器包
提供统一的文件存储接口，支持多种存储提供商
"""

from .manager import StorageManager, initialize_storage, get_storage_manager, set_storage_manager
from .base import StorageProvider
from .auth import init_google_cloud_auth, init_all_auth

__all__ = [
    'StorageManager',
    'StorageProvider', 
    'initialize_storage',
    'get_storage_manager',
    'set_storage_manager',
    'init_google_cloud_auth',
    'init_all_auth'
]