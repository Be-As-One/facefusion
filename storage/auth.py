"""
存储认证工具 - 处理各种存储提供商的认证
"""
import os
import base64
import json
import logging


logger = logging.getLogger(__name__)


def init_google_cloud_auth():
    """
    初始化 Google Cloud 认证
    处理 Base64 编码的凭据和认证文件设置
    """
    try:
        # 从环境变量中读取 Base64 编码的凭据
        credentials_base64 = os.getenv('GOOGLE_CREDENTIALS_BASE64')
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if credentials_base64 and credentials_path:
            logger.info("🔧 解码 Base64 编码的 Google Cloud 凭据")
            decoded = base64.b64decode(credentials_base64).decode("utf-8")
            
            # 验证 JSON 格式
            json.loads(decoded)
            
            # 确保凭据文件目录存在
            os.makedirs(os.path.dirname(credentials_path), exist_ok=True)
            
            # 写入到指定的凭据文件路径
            with open(credentials_path, 'w', encoding='utf-8') as f:
                f.write(decoded)
            
            logger.info(f"✅ Google Cloud 认证文件已创建: {credentials_path}")
            return credentials_path
        
        # 检查是否已经设置了 GOOGLE_APPLICATION_CREDENTIALS 且文件存在
        if credentials_path and os.path.exists(credentials_path):
            logger.info(f"✅ 使用现有的 Google Cloud 认证文件: {credentials_path}")
            return credentials_path
        
        logger.warning("⚠️ 未找到 Google Cloud 认证配置，GCS 存储功能可能受限")
        return None
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Google Cloud 凭据 JSON 格式错误: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ 初始化 Google Cloud 认证失败: {e}")
        return None


def init_all_auth():
    """
    初始化所有存储提供商的认证
    目前主要是 Google Cloud，后续可以扩展其他提供商
    """
    logger.info("🔑 开始初始化存储认证...")
    
    # 初始化 Google Cloud 认证
    gcs_auth_result = init_google_cloud_auth()
    
    # 可以在这里添加其他存储提供商的认证初始化
    # 例如：AWS S3, Azure, 等等
    
    auth_results = {
        'gcs': gcs_auth_result is not None,
        'gcs_credentials_path': gcs_auth_result
    }
    
    logger.info("✅ 存储认证初始化完成")
    return auth_results