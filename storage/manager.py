"""
存储管理器 - 统一管理多种存储提供商
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from .config import (
    storage_provider as default_storage_provider,
    bucket_name, 
    cdn_url,
    r2_bucket_name,
    r2_account_id,
    r2_access_key,
    r2_secret_key,
    r2_public_domain,
    cf_images_account_id,
    cf_images_api_token,
    cf_images_delivery_domain
)
from .base import StorageProvider


logger = logging.getLogger(__name__)


class StorageManager:
    """存储管理器 - 统一管理多种存储提供商"""

    def __init__(self):
        self.providers = {}
        self.default_provider = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._initialized = False

    def register_provider(self, name: str, provider: StorageProvider, is_default: bool = False):
        """注册存储提供商"""
        self.providers[name] = provider
        if is_default or self.default_provider is None:
            self.default_provider = name
        logger.info(f"📦 注册存储提供商: {name}")

    def get_provider(self, name: str = None) -> StorageProvider:
        """获取存储提供商"""
        provider_name = name or self.default_provider
        if provider_name not in self.providers:
            raise ValueError(f"Storage provider '{provider_name}' not found")
        return self.providers[provider_name]

    def upload_file(self, source_file_name: str, destination_path: str, provider: str = None) -> str:
        """上传文件"""
        return self.get_provider(provider).upload_file(source_file_name, destination_path)

    def upload_binary(self, binary_data: bytes, destination_path: str, provider: str = None) -> str:
        """上传二进制数据"""
        if not self.is_initialized():
            raise RuntimeError("存储管理器未初始化，请先调用 initialize() 方法")

        provider_name = provider or self.default_provider
        logger.info(f"使用存储提供商上传: {provider_name}")
        logger.debug(f"上传路径: {destination_path}, 数据大小: {len(binary_data)} bytes")

        try:
            result = self.get_provider(provider).upload_binary(binary_data, destination_path)
            logger.info(f"存储管理器上传成功: {result}")
            return result
        except Exception as e:
            logger.error(f"存储管理器上传失败: {str(e)}")
            logger.error(f"提供商: {provider_name}, 路径: {destination_path}")
            raise

    def upload_base64(self, base64_data: str, destination_path: str, provider: str = None) -> str:
        """上传base64数据"""
        return self.get_provider(provider).upload_base64(base64_data, destination_path)

    def upload_file_async(self, source_file_name: str, destination_path: str, provider: str = None):
        """异步上传文件"""
        future = self.executor.submit(self.upload_file, source_file_name, destination_path, provider)
        return future

    def upload_binary_async(self, binary_data: bytes, destination_path: str, provider: str = None):
        """异步上传二进制数据"""
        future = self.executor.submit(self.upload_binary, binary_data, destination_path, provider)
        return future

    def initialize(self):
        """初始化存储管理器，配置所有可用的存储提供商"""
        if self._initialized:
            logger.debug("存储管理器已经初始化，跳过")
            return

        logger.info("🔧 开始初始化存储管理器...")

        # 首先初始化认证
        try:
            from .auth import init_all_auth
            auth_results = init_all_auth()
            logger.debug(f"认证结果: {auth_results}")
        except Exception as e:
            logger.warning(f"⚠️ 认证初始化失败: {e}")

        self.providers.clear()
        self.default_provider = None

        # 直接使用 config.py 中的配置
        logger.debug(f"配置的存储提供商: {default_storage_provider}")

        # 动态导入和配置提供商
        self._configure_gcs(default_storage_provider)
        self._configure_r2(default_storage_provider)
        self._configure_cf_images(default_storage_provider)

        if not self.providers:
            logger.warning("⚠️ No storage providers configured, file uploads will be disabled")
        else:
            logger.info(f"📦 Storage manager initialized with providers: {list(self.providers.keys())}")
            logger.info(f"📦 Default provider: {self.default_provider}")

        self._initialized = True
        logger.info("✅ 存储管理器初始化完成")

    def _configure_gcs(self, storage_provider: str):
        """配置GCS提供商"""
        if storage_provider == 'gcs' and bucket_name:
            try:
                from .providers.gcs import GCSProvider
                logger.debug(f"配置 GCS bucket: {bucket_name}")
                logger.debug(f"配置 GCS CDN URL: {cdn_url}")
                gcs_provider = GCSProvider(bucket_name, cdn_url=cdn_url)
                self.register_provider('gcs', gcs_provider, is_default=(storage_provider == 'gcs'))
                logger.info("✅ GCS provider configured")
            except ImportError:
                logger.warning("⚠️ google-cloud-storage not installed, skipping GCS provider")
            except Exception as e:
                logger.warning(f"⚠️ Failed to configure GCS provider: {e}")

    def _configure_r2(self, storage_provider: str):
        """配置Cloudflare R2提供商"""
        if storage_provider == 'r2' and all([r2_bucket_name, r2_account_id, r2_access_key, r2_secret_key]):
            try:
                from .providers.cloudflare_r2 import CloudflareR2Provider
                logger.debug(f"配置 R2 bucket: {r2_bucket_name}")
                r2_provider = CloudflareR2Provider(
                        bucket_name=r2_bucket_name,
                        account_id=r2_account_id,
                        access_key=r2_access_key,
                        secret_key=r2_secret_key,
                        public_domain=r2_public_domain
                    )
                self.register_provider('r2', r2_provider, is_default=(storage_provider == 'r2'))
                logger.info("✅ Cloudflare R2 provider configured")
            except ImportError:
                logger.warning("⚠️ boto3 not installed, skipping R2 provider")
            except Exception as e:
                logger.warning(f"⚠️ Failed to configure R2 provider: {e}")

    def _configure_cf_images(self, storage_provider: str):
        """配置Cloudflare Images提供商"""
        if storage_provider == 'cf_images' and all([cf_images_account_id, cf_images_api_token]):
            try:
                from .providers.cloudflare_images import CloudflareImagesProvider
                logger.debug(f"配置 Cloudflare Images Account ID: {cf_images_account_id}")
                cf_images_provider = CloudflareImagesProvider(
                        account_id=cf_images_account_id,
                        api_token=cf_images_api_token,
                        delivery_domain=cf_images_delivery_domain
                    )
                self.register_provider('cf_images', cf_images_provider, is_default=(storage_provider == 'cf_images'))
                logger.info("✅ Cloudflare Images provider configured")
            except ImportError:
                logger.warning("⚠️ requests not installed, skipping Cloudflare Images provider")
            except Exception as e:
                logger.warning(f"⚠️ Failed to configure Cloudflare Images provider: {e}")

    def is_initialized(self) -> bool:
        """检查存储管理器是否已初始化"""
        return self._initialized and bool(self.providers)


# 全局存储管理器实例变量
_global_storage_manager = None


def get_storage_manager() -> StorageManager:
    """获取全局存储管理器实例"""
    global _global_storage_manager
    if _global_storage_manager is None:
        raise RuntimeError("存储管理器未初始化，请先调用 set_storage_manager() 设置实例")
    return _global_storage_manager


def set_storage_manager(manager: StorageManager):
    """设置全局存储管理器实例"""
    global _global_storage_manager
    _global_storage_manager = manager


def initialize_storage():
    """初始化全局存储管理器"""
    manager = StorageManager()
    manager.initialize()
    set_storage_manager(manager)
    return manager


def upload_binary_image(binary_data: bytes, destination_path: str) -> str:
    """向后兼容：上传二进制图片"""
    return get_storage_manager().upload_binary(binary_data, destination_path)