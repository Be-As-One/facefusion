#!/usr/bin/env python3
"""
简化的 RunPod Serverless Handler for FaceFusion
直接使用 FaceFusion 核心功能，不依赖 fastapi 子模块
"""

import logging
import os
import sys
import time
import traceback
import tempfile
import urllib.request
import urllib.error
from typing import Any, Dict
from pathlib import Path

# 设置环境变量
os.environ['OMP_NUM_THREADS'] = '1'

# 导入 RunPod SDK (可选)
try:
    import runpod
    RUNPOD_AVAILABLE = True
except ImportError:
    RUNPOD_AVAILABLE = False
    logger.warning("RunPod SDK 不可用，将在本地测试模式下运行")

# 添加项目路径到 Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入 FaceFusion 核心模块
from facefusion.core import cli, conditional_process
from facefusion import state_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def headless_conditional_process(sources, target, output, resolution, face_swapper_model):
    """自定义的 FaceFusion 处理函数"""
    try:
        # 设置所有必要的状态
        state_manager.set_item('source_paths', sources)
        state_manager.set_item('target_path', target)
        state_manager.set_item('output_path', output)
        state_manager.set_item('output_image_resolution', resolution)
        state_manager.set_item('output_video_resolution', resolution)
        state_manager.set_item('output_video_fps', 30)
        state_manager.set_item('face_swapper_model', face_swapper_model)
        
        # 设置临时路径
        temp_path = tempfile.gettempdir()
        state_manager.set_item('temp_path', temp_path)
        
        # 直接调用处理器
        from facefusion.processors.modules import face_swapper
        
        # 验证源路径存在
        if not sources or not all(os.path.exists(p) for p in sources):
            logger.error("源文件不存在")
            return 1
        
        if not os.path.exists(target):
            logger.error("目标文件不存在")
            return 1
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 调用 face_swapper 处理图片
        face_swapper.process_image(sources, target, output)
        
        if os.path.exists(output):
            logger.info(f"处理成功，输出文件: {output}")
            return 0
        else:
            logger.error("输出文件未生成")
            return 1
            
    except Exception as e:
        logger.error(f"处理过程中出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


class SimpleFaceFusionHandler:
    """简化的 FaceFusion 处理器"""
    
    def __init__(self):
        self.is_initialized = False
        
    def initialize(self):
        """初始化 FaceFusion"""
        if self.is_initialized:
            return
            
        try:
            logger.info("正在初始化 FaceFusion...")
            
            # 初始化必要的默认参数 (FaceFusion 3.3.0)
            default_args = {
                'processors': ['face_swapper'],
                'face_swapper_model': 'inswapper_128_fp16',
                'face_swapper_pixel_boost': '128x128',
                'face_detector_model': 'yolo_face',
                'face_detector_score': 0.5,
                'face_detector_size': '640x640',
                'face_detector_angles': [0],
                'face_landmarker_model': '2dfan4',
                'face_landmarker_score': 0.5,
                'face_selector_mode': 'many',
                'face_selector_order': 'large-small',
                'reference_face_position': 0,
                'reference_face_distance': 0.3,
                'reference_frame_number': 0,
                'face_mask_types': ['box'],
                'face_mask_blur': 0.3,
                'face_mask_padding': [0, 0, 0, 0],
                'temp_frame_format': 'png',
                'output_image_quality': 80,
                'output_video_encoder': 'libx264',
                'output_video_preset': 'veryfast',
                'execution_device_id': '0',
                'execution_providers': ['cpu'],
                'execution_thread_count': 1,
                'execution_queue_count': 1,
                'download_providers': ['github', 'huggingface'],
                'download_scope': 'full',
                'video_memory_strategy': 'strict',
                'system_memory_limit': 0,
                'log_level': 'info'
            }
            
            # 应用默认参数到 state_manager
            for key, value in default_args.items():
                state_manager.init_item(key, value)
            
            self.is_initialized = True
            logger.info("FaceFusion 初始化完成")
            
        except Exception as e:
            logger.error(f"初始化失败: {str(e)}")
            raise e
    
    def download_file(self, url: str, local_path: str) -> bool:
        """下载文件到本地"""
        try:
            logger.info(f"下载文件: {url} -> {local_path}")
            
            # 使用 urllib 替代 requests
            with urllib.request.urlopen(url, timeout=30) as response:
                with open(local_path, 'wb') as f:
                    f.write(response.read())
            
            logger.info(f"文件下载完成: {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"下载文件失败: {str(e)}")
            return False
    
    def process_face_swap(self, source_url: str, target_url: str, output_path: str, resolution: str = "1024x1024") -> Dict[str, Any]:
        """执行人脸交换"""
        temp_dir = None
        
        try:
            # 确保初始化
            if not self.is_initialized:
                self.initialize()
            
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            logger.info(f"创建临时目录: {temp_dir}")
            
            # 下载源文件和目标文件
            # 从 URL 中提取真实的文件扩展名，处理查询参数
            def get_file_extension(url):
                parsed_url = url.split('?')[0]  # 移除查询参数
                ext = Path(parsed_url).suffix
                return ext if ext else '.jpg'
            
            source_ext = get_file_extension(source_url)
            target_ext = get_file_extension(target_url)
            
            source_path = os.path.join(temp_dir, f"source{source_ext}")
            target_path = os.path.join(temp_dir, f"target{target_ext}")
            
            if not self.download_file(source_url, source_path):
                raise Exception("下载源文件失败")
            
            if not self.download_file(target_url, target_path):
                raise Exception("下载目标文件失败")
            
            logger.info(f"开始处理人脸交换: {resolution}")
            start_time = time.time()
            
            # 使用正确的 FaceFusion 处理方式
            face_swapper_model = 'inswapper_128_fp16'
            headless_conditional_process(
                sources=[source_path],
                target=target_path,
                output=output_path,
                resolution=resolution,
                face_swapper_model=face_swapper_model
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            logger.info(f"人脸交换完成: {output_path} ({processing_time:.2f}s)")
            
            # 检查输出文件是否存在
            if os.path.exists(output_path):
                return {
                    'status': 'success',
                    'output_path': output_path,
                    'processing_time': processing_time,
                    'message': '人脸交换完成'
                }
            else:
                raise Exception("输出文件未生成")
                
        except Exception as e:
            logger.error(f"人脸交换处理失败: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        
        finally:
            # 清理临时文件
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                    logger.info(f"清理临时目录: {temp_dir}")
                except Exception as e:
                    logger.warning(f"清理临时目录失败: {str(e)}")


# 全局处理器实例
handler_instance = SimpleFaceFusionHandler()


def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod Handler 主函数
    
    Args:
        job: RunPod 作业输入，包含以下字段：
            - input: 用户输入参数
                - source_url: 源人脸图片URL
                - target_url: 目标图片URL
                - resolution: 输出分辨率 (默认: "1024x1024")
    
    Returns:
        Dict: 处理结果
    """
    try:
        logger.info(f"收到新请求: {job.get('id', 'unknown')}")
        
        # 提取输入参数
        job_input = job.get('input', {})
        source_url = job_input.get('source_url')
        target_url = job_input.get('target_url')
        resolution = job_input.get('resolution', '1024x1024')
        
        # 输入验证
        if not source_url or not target_url:
            raise ValueError("source_url 和 target_url 是必需的参数")
        
        # 创建输出文件路径，扩展名与目标文件匹配
        output_dir = tempfile.mkdtemp()
        # 处理 URL 查询参数，提取真实扩展名
        parsed_target_url = target_url.split('?')[0]
        target_ext = Path(parsed_target_url).suffix or '.jpg'
        output_filename = f'output{target_ext}'
        output_path = os.path.join(output_dir, output_filename)
        
        # 处理人脸交换
        result = handler_instance.process_face_swap(
            source_url=source_url,
            target_url=target_url,
            output_path=output_path,
            resolution=resolution
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Handler 执行失败: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def sync_handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """同步包装器，用于 RunPod"""
    return handler(job)


def health_check():
    """健康检查"""
    try:
        return {
            'status': 'healthy',
            'timestamp': time.time(),
            'facefusion_initialized': handler_instance.is_initialized
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }


if __name__ == "__main__":
    # 本地测试模式
    if len(sys.argv) > 1 and '--test' in sys.argv:
        logger.info("运行本地测试...")
        
        test_job = {
            "id": "test-001",
            "input": {
                "source_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=512&h=512&fit=crop&crop=face",
                "target_url": "https://test.deepswaper.net/_next/image?url=https%3A%2F%2Fcdn-test.deepswaper.net%2F%2Fface-swap%2F2.png&w=256&q=75",
                "resolution": "512x512"
            }
        }
        
        result = handler(test_job)
        print(f"测试结果: {result}")
    else:
        # 启动 RunPod 服务器
        if RUNPOD_AVAILABLE:
            logger.info("启动 RunPod FaceFusion Handler...")
            runpod.serverless.start({"handler": handler})
        else:
            logger.error("RunPod SDK 不可用，无法启动服务器")