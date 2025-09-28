#!/usr/bin/env python3
"""
RunPod FaceFusion 人脸交换处理器 - 简化版
使用统一的 FusionManager 核心逻辑
"""

import asyncio
import logging
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict
from fusion_manager import FaceFusionManager, ProcessRequest

# ============================================================================
# 基础配置
# ============================================================================

# 项目路径设置
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 可选依赖检查
try:
    import runpod
    RUNPOD_AVAILABLE = True
    print("✅ RunPod SDK 导入成功")
except ImportError as e:
    RUNPOD_AVAILABLE = False
    print(f"❌ RunPod SDK 导入失败: {e}")
    print("💡 如果在 Docker 容器中，请确保 requirements.txt 中包含 runpod")

# ============================================================================
# 全局管理器实例
# ============================================================================

# 创建全局处理器实例
fusion_manager = FaceFusionManager()

# 添加同步包装函数
def sync_process_face_swap(source_url: str, target_url: str, resolution: str, model: str, job_id: str):
    """同步包装异步面部交换处理"""
    request = ProcessRequest(source_url, target_url, resolution, model)
    
    # 确保 FaceFusion 已初始化
    if not fusion_manager.initialized:
        fusion_manager.initialize()
    
    # 运行异步处理
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(fusion_manager.process_face_swap(request))
        return result
    finally:
        loop.close()




def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod 主处理函数 - 对外接口
    
    输入格式 (job):
    {
        "id": "任务ID",
        "input": {
            "source_url": "源图片URL",      # 必需 - 包含要交换人脸的图片
            "target_url": "目标图片URL",    # 必需 - 要被换脸的目标图片  
            "resolution": "1024x1024",     # 可选 - 输出分辨率
            "model": "inswapper_128_fp16"  # 可选 - AI模型名称
        }
    }
    
    输出格式:
    {
        "status": "成功/失败",
        "output_path": "输出文件路径",     # 成功时提供
        "processing_time": 处理耗时秒数,
        "error": "错误描述",              # 失败时提供
        "job_id": "任务ID"
    }
    """
    logger = logging.getLogger("RunPod处理器")
    job_id = job.get('id', '未知任务')
    
    try:
        logger.info(f"🎯 接收到任务: {job_id}")
        
        # 提取和验证输入参数
        job_input = job.get('input', {})
        source_url = job_input.get('source_url')
        target_url = job_input.get('target_url')
        resolution = job_input.get('resolution', '1024x1024')
        model = job_input.get('model', 'inswapper_128_fp16')
        
        # 输入验证
        if not source_url or not target_url:
            raise ValueError("❌ source_url 和 target_url 是必需的参数")
        
        # 验证分辨率格式
        if not resolution.count('x') == 1:
            raise ValueError("❌ resolution 格式错误，应为 'widthxheight' 如 '1024x1024'")
        
        # 处理请求
        result = sync_process_face_swap(
            source_url=source_url,
            target_url=target_url,
            resolution=resolution,
            model=model,
            job_id=job_id
        )
        
        # 准备响应
        response = result.to_dict()
        response['job_id'] = job_id
        
        logger.info(f"📤 任务 {job_id} 处理完成: {result.status}")
        return response
        
    except Exception as error:
        logger.error(f"❌ 任务 {job_id} 执行失败: {str(error)}")
        return {
            'status': '失败',
            'error': str(error),
            'traceback': traceback.format_exc(),
            'job_id': job_id
        }


def health_check() -> Dict[str, Any]:
    """系统健康检查接口"""
    try:
        return {
            'status': 'healthy',
            'service': 'FaceFusion 人脸交换服务',
            'version': '3.3.0 中文优化版',
            'description': '智能人脸交换处理系统',
            'initialized': fusion_manager.initialized,
            'timestamp': time.time()
        }
    except Exception as error:
        return {
            'status': 'unhealthy',
            'error': str(error),
            'timestamp': time.time()
        }


def setup_logging(level: str = "INFO") -> None:
    """配置中文化的日志系统"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # 调整第三方库日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('facefusion').setLevel(logging.INFO)


# ============================================================================
# 主程序入口
# ============================================================================

if __name__ == "__main__":
    # 设置日志系统
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 本地测试模式
    if len(sys.argv) > 1 and '--test' in sys.argv:
        logger.info("🧪 启动本地测试模式...")
        
        test_job = {
            "id": "本地测试-001",
            "input": {
                "source_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=512&h=512&fit=crop&crop=face",
                "target_url": "https://images.unsplash.com/photo-1494790108755-2616b612b5bc?w=512&h=512&fit=crop&crop=face",
                "resolution": "512x512"
            }
        }
        
        print("\n" + "=" * 60)
        print("🎭 FaceFusion 人脸交换系统测试")
        print("=" * 60)
        
        result = handler(test_job)
        print(f"\n📊 测试结果:")
        for key, value in result.items():
            print(f"   {key}: {value}")
        
        # 显示系统统计
        stats = health_check()
        print(f"\n📈 系统统计:")
        for key, value in stats.items():
            if key not in ['status', 'service', 'version', 'description']:
                print(f"   {key}: {value}")
        print("\n" + "=" * 60)
        
    else:
        # 启动 RunPod 服务器
        if RUNPOD_AVAILABLE:
            logger.info("🚀 启动 RunPod FaceFusion 人脸交换服务...")
            logger.info("📋 服务配置:")
            logger.info(f"   🎯 人脸检测模型: yolo_face")
            logger.info(f"   🤖 人脸交换模型: inswapper_128_fp16")
            logger.info(f"   ⚡ 执行提供商: cpu")
            logger.info(f"   💾 显存策略: moderate")
            
            runpod.serverless.start({
                "handler": handler,
                "return_aggregate_stream": True
            })
        else:
            logger.error("❌ RunPod SDK 不可用，无法启动服务器")
            logger.info("💡 安装提示: pip install runpod")

            