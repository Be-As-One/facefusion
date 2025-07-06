"""
存储相关配置
"""
import os


def get_env_bool(key: str, default: bool = False) -> bool:
    """获取布尔类型环境变量"""
    return os.getenv(key, str(default)).lower() in ('true', '1', 'yes', 'on')


def get_env_int(key: str, default: int) -> int:
    """获取整数类型环境变量"""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


# 存储配置
storage_provider = os.getenv('STORAGE_PROVIDER', 'local')  # 'local', 'gcs', 'r2', 'cf_images'

# 本地存储配置
local_storage_path = os.getenv('LOCAL_STORAGE_PATH', '/workspace/results')

# Google Cloud Storage 配置
bucket_name = os.getenv('GCS_BUCKET_NAME', '')
bucket_region = os.getenv('GCS_BUCKET_REGION', 'us-east-1')
cdn_url = os.getenv('CDN_URL', '')

# Cloudflare R2 配置
r2_bucket_name = os.getenv('R2_BUCKET_NAME', '')
r2_account_id = os.getenv('R2_ACCOUNT_ID', '')
r2_access_key = os.getenv('R2_ACCESS_KEY', '')
r2_secret_key = os.getenv('R2_SECRET_KEY', '')
r2_public_domain = os.getenv('R2_PUBLIC_DOMAIN', '')

# Cloudflare Images 配置
cf_images_account_id = os.getenv('CF_IMAGES_ACCOUNT_ID', '')
cf_images_api_token = os.getenv('CF_IMAGES_API_TOKEN', '')
cf_images_delivery_domain = os.getenv('CF_IMAGES_DELIVERY_DOMAIN', '')