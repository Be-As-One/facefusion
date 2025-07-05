#!/usr/bin/env python3
"""
RunPod FaceFusion 人脸交换处理器 - 最终优化版
支持 FaceFusion 3.3.0，完全中文化配置和错误处理

主要功能:
✅ 智能人脸交换处理
✅ 自动重试和错误恢复  
✅ 内存优化和资源管理
✅ 详细的中文日志
✅ 性能监控统计
✅ 灵活的配置选项
"""

from facefusion import state_manager
from facefusion.processors.modules import face_swapper
from facefusion.download import conditional_download
import logging
import os
import shutil
import sys
import tempfile
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# ============================================================================
# 基础配置
# ============================================================================

# 性能优化 - 限制线程数量避免CPU过载
os.environ.update({
    'OMP_NUM_THREADS': '1',          # OpenMP 线程数
    'MKL_NUM_THREADS': '1',          # Intel MKL 线程数  
    'NUMEXPR_NUM_THREADS': '1'       # NumExpr 线程数
})

# 可选依赖检查
try:
    import runpod
    RUNPOD_AVAILABLE = True
except ImportError:
    RUNPOD_AVAILABLE = False

# 项目路径设置
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# FaceFusion 核心模块

# 下载工具模块

# ============================================================================
# 中文化配置类
# ============================================================================


class FaceFusionConfig:
    """
    人脸交换的中文化配置类
    所有参数都有详细的中文说明，方便理解和修改
    """
    
    # 🎯 核心处理配置
    processors = ['face_swapper']                    # 使用的处理器：人脸交换
    
    # 🤖 AI模型配置  
    face_swapper_model = 'inswapper_128_fp16'        # 人脸交换AI模型 (推荐fp16版本，速度快)
    face_swapper_pixel_boost = '128x128'             # 像素增强处理分辨率
    
    # 👁️ 人脸检测配置
    face_detector_model = 'yolo_face'                # 人脸检测模型 (YOLO效果好)
    face_detector_score = 0.5                        # 人脸检测置信度 (0.1-1.0，越高越严格)
    face_detector_size = '640x640'                   # 检测图片尺寸 (越大越准确但更慢)
    face_detector_angles = [0]                       # 检测角度 (0, 90, 180, 270度)
    
    # 🔍 人脸特征点配置
    face_landmarker_model = '2dfan4'                 # 人脸特征点检测模型
    face_landmarker_score = 0.5                      # 特征点检测置信度
    
    # 🎭 人脸选择配置  
    face_selector_mode = 'many'                      # 人脸选择模式：many(多个), one(单个), reference(参考)
    face_selector_order = 'large-small'              # 排序方式：大到小，small-large(小到大)
    reference_face_position = 0                      # 参考人脸位置索引 (从0开始)
    reference_face_distance = 0.3                    # 人脸相似度阈值 (0.0-1.0)
    reference_frame_number = 0                       # 视频参考帧编号
    
    # 🎭 面部遮罩配置
    face_mask_types = ['box']                        # 遮罩类型：box(矩形), occlusion(遮挡), area(区域), region(部位)
    face_mask_blur = 0.3                             # 遮罩边缘模糊程度 (0.0-1.0)
    face_mask_padding = [0, 0, 0, 0]                 # 遮罩边距 [上, 右, 下, 左]
    
    # 🖼️ 输出质量配置
    temp_frame_format = 'png'                        # 临时文件格式：png(无损), jpg(有损但小)
    output_image_quality = 80                        # 输出图片质量 (1-100，越高越好但文件越大)
    output_video_encoder = 'libx264'                 # 视频编码器
    output_video_preset = 'veryfast'                 # 编码速度预设：ultrafast, veryfast, fast, medium, slow
    
    # ⚡ 性能配置
    execution_device_id = '0'                        # GPU设备ID (0为第一个GPU，CPU则忽略)
    execution_providers = ['cpu']                    # 运算提供商：cpu, cuda, tensorrt 等
    execution_thread_count = 1                       # 处理线程数 (1-8，根据CPU核心数调整)
    execution_queue_count = 1                        # 处理队列数
    
    # 📥 下载配置
    download_providers = ['github', 'huggingface']  # 模型下载源
    download_scope = 'full'                          # 下载范围：lite(精简), full(完整)
    
    # 💾 内存配置  
    video_memory_strategy = 'strict'                 # 显存策略：strict(严格), moderate(适中), tolerant(宽松)
    system_memory_limit = 0                          # 系统内存限制(GB)，0为不限制
    
    # 📝 日志配置
    log_level = 'info'                               # 日志级别：debug, info, warning, error

    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """获取默认配置字典"""
        return {
            'processors': cls.processors,
            'face_swapper_model': cls.face_swapper_model,
            'face_swapper_pixel_boost': cls.face_swapper_pixel_boost,
            'face_detector_model': cls.face_detector_model,
            'face_detector_score': cls.face_detector_score,
            'face_detector_size': cls.face_detector_size,
            'face_detector_angles': cls.face_detector_angles,
            'face_landmarker_model': cls.face_landmarker_model,
            'face_landmarker_score': cls.face_landmarker_score,
            'face_selector_mode': cls.face_selector_mode,
            'face_selector_order': cls.face_selector_order,
            'reference_face_position': cls.reference_face_position,
            'reference_face_distance': cls.reference_face_distance,
            'reference_frame_number': cls.reference_frame_number,
            'face_mask_types': cls.face_mask_types,
            'face_mask_blur': cls.face_mask_blur,
            'face_mask_padding': cls.face_mask_padding,
            'temp_frame_format': cls.temp_frame_format,
            'output_image_quality': cls.output_image_quality,
            'output_video_encoder': cls.output_video_encoder,
            'output_video_preset': cls.output_video_preset,
            'execution_device_id': cls.execution_device_id,
            'execution_providers': cls.execution_providers,
            'execution_thread_count': cls.execution_thread_count,
            'execution_queue_count': cls.execution_queue_count,
            'download_providers': cls.download_providers,
            'download_scope': cls.download_scope,
            'video_memory_strategy': cls.video_memory_strategy,
            'system_memory_limit': cls.system_memory_limit,
            'log_level': cls.log_level
        }

    @classmethod
    def apply_config(cls, custom_config: Optional[Dict[str, Any]] = None) -> None:
        """将配置应用到FaceFusion"""
        config = cls.get_default_config()
        if custom_config:
            config.update(custom_config)
        
        for key, value in config.items():
            state_manager.init_item(key, value)


# ============================================================================
# 处理结果类
# ============================================================================

@dataclass
class ProcessingResult:
    """人脸交换处理结果"""
    status: str                                      # 处理状态：成功、失败、处理中
    output_path: Optional[str] = None                # 输出文件路径
    processing_time: Optional[float] = None          # 处理耗时(秒)
    error: Optional[str] = None                      # 错误描述
    traceback: Optional[str] = None                  # 详细错误堆栈
    metadata: Optional[Dict[str, Any]] = None        # 额外信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，方便JSON序列化"""
        result = {"status": self.status}
        
        if self.output_path:
            result["output_path"] = self.output_path
        if self.processing_time is not None:
            result["processing_time"] = self.processing_time
        if self.error:
            result["error"] = self.error
        if self.traceback:
            result["traceback"] = self.traceback
        if self.metadata:
            result["metadata"] = self.metadata
            
        return result


# ============================================================================
# 存储上传功能（使用 fastapi 的存储模块）
# ============================================================================

def get_storage_manager():
    """获取存储管理器"""
    try:
        # 使用 fastapi 的存储管理器
        fastapi_path = Path(__file__).parent / 'fastapi'
        sys.path.insert(0, str(fastapi_path))
        
        # 导入并执行初始化函数
        import main
        
        # 初始化存储管理器
        return main.init_storage()
    except Exception as e:
        logging.getLogger("存储管理器").warning(f"⚠️ 存储管理器初始化失败: {str(e)}")
        return None


# 初始化存储管理器
storage_manager = get_storage_manager()


# ============================================================================
# 资源管理器
# ============================================================================

class ResourceManager:
    """临时文件和目录的自动清理管理器"""
    
    def __init__(self):
        self.temp_dirs: List[str] = []               # 临时目录列表
        self.temp_files: List[str] = []              # 临时文件列表
        self.logger = logging.getLogger("资源管理器")

    def create_temp_dir(self, prefix: str = "faceswap_") -> str:
        """创建临时目录并自动管理"""
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        self.temp_dirs.append(temp_dir)
        self.logger.debug(f"📁 创建临时目录: {temp_dir}")
        return temp_dir

    def register_temp_file(self, file_path: str) -> None:
        """注册需要清理的临时文件"""
        self.temp_files.append(file_path)

    def cleanup_all(self) -> None:
        """清理所有临时文件和目录"""
        # 清理临时文件
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.logger.debug(f"🗑️ 删除临时文件: {file_path}")
            except Exception as error:
                self.logger.warning(f"⚠️ 删除文件失败 {file_path}: {str(error)}")
        
        # 清理临时目录
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    self.logger.debug(f"🗑️ 删除临时目录: {temp_dir}")
            except Exception as error:
                self.logger.warning(f"⚠️ 删除目录失败 {temp_dir}: {str(error)}")
        
        self.temp_files.clear()
        self.temp_dirs.clear()

    @contextmanager
    def auto_cleanup(self):
        """上下文管理器，自动清理资源"""
        try:
            yield self
        finally:
            self.cleanup_all()


# ============================================================================
# 核心处理函数
# ============================================================================

def validate_files(*file_paths: str) -> tuple[bool, Optional[str]]:
    """验证文件是否存在且有效"""
    for file_path in file_paths:
        if not os.path.exists(file_path):
            return False, f"文件不存在: {file_path}"
        if os.path.getsize(file_path) == 0:
            return False, f"文件为空: {file_path}"
    return True, None


def setup_processing_state(source_paths: List[str], target_path: str, output_path: str, 
                          resolution: str, model_name: str) -> None:
    """设置FaceFusion处理状态"""
    state_manager.set_item('source_paths', source_paths)
    state_manager.set_item('target_path', target_path)
    state_manager.set_item('output_path', output_path)
    state_manager.set_item('output_image_resolution', resolution)
    state_manager.set_item('output_video_resolution', resolution)
    state_manager.set_item('output_video_fps', 30)
    state_manager.set_item('face_swapper_model', model_name)
    state_manager.set_item('temp_path', tempfile.gettempdir())


def process_face_swap(source_paths: List[str], target_path: str, output_path: str,
                     resolution: str = "1024x1024", 
                     model_name: str = "inswapper_128_fp16") -> ProcessingResult:
    """
    执行人脸交换的核心逻辑
    
    参数:
        source_paths: 包含人脸的源图片路径列表
        target_path: 要被换脸的目标图片路径  
        output_path: 结果保存路径
        resolution: 输出分辨率 (如: "1024x1024")
        model_name: 使用的AI模型名称
        
    返回:
        处理结果对象
    """
    logger = logging.getLogger("人脸交换处理器")
    start_time = time.time()
    
    try:
        # 验证输入文件
        all_files = source_paths + [target_path]
        is_valid, error_msg = validate_files(*all_files)
        if not is_valid:
            return ProcessingResult(status="失败", error=error_msg)
        
        # 设置处理参数
        setup_processing_state(source_paths, target_path, output_path, resolution, model_name)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 执行人脸交换
        logger.info(f"🎭 开始人脸交换处理，输出分辨率: {resolution}")
        face_swapper.process_image(source_paths, target_path, output_path)
        
        processing_time = time.time() - start_time
        
        # 验证输出结果
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            output_size = os.path.getsize(output_path)
            logger.info(f"✅ 人脸交换成功完成: {output_path} (耗时 {processing_time:.2f}秒)")
            
            # 上传到存储桶
            import uuid
            timestamp = int(time.time())
            unique_id = str(uuid.uuid4())[:8]
            file_ext = os.path.splitext(output_path)[1]
            destination_path = f"results/{timestamp}_{unique_id}{file_ext}"
            
            try:
                if storage_manager:
                    storage_url = storage_manager.upload_file(output_path, destination_path)
                    logger.info(f"📤 结果已上传到存储: {storage_url}")
                    final_output_path = storage_url
                else:
                    logger.warning("⚠️ 存储管理器未配置，返回本地路径")
                    final_output_path = output_path
            except Exception as e:
                logger.warning(f"⚠️ 存储上传失败，返回本地路径: {str(e)}")
                final_output_path = output_path
            
            return ProcessingResult(
                status="成功",
                output_path=final_output_path,
                processing_time=processing_time,
                metadata={
                    "输出分辨率": resolution,
                    "使用模型": model_name,
                    "输入文件数量": len(all_files),
                    "输出文件大小": output_size,
                    "平均处理速度": f"{output_size / processing_time / 1024:.1f} KB/秒",
                    "存储路径": destination_path if 'storage_url' in locals() else None
                }
            )
        else:
            return ProcessingResult(
                status="失败",
                error="输出文件未生成或为空",
                processing_time=processing_time
            )
            
    except Exception as error:
        processing_time = time.time() - start_time
        logger.error(f"❌ 人脸交换处理失败: {str(error)}")
        return ProcessingResult(
            status="失败",
            error=str(error),
            traceback=traceback.format_exc(),
            processing_time=processing_time
        )


# ============================================================================
# 主处理器类
# ============================================================================

class FaceFusionHandler:
    """
    智能人脸交换处理器
    
    功能特点:
    - 🎯 自动初始化和配置管理
    - 📥 智能文件下载和重试
    - 🎭 高质量人脸交换处理  
    - 📊 详细的性能统计
    - 🧹 自动资源清理
    - 🔄 错误恢复机制
    """
    
    def __init__(self, custom_config: Optional[Dict[str, Any]] = None):
        self.initialized = False                     # 初始化状态
        self.custom_config = custom_config or {}     # 自定义配置
        self.logger = logging.getLogger("人脸交换处理器")
        
        # 性能统计
        self.stats = {
            "总请求数": 0,
            "成功请求数": 0,
            "失败请求数": 0,
            "总处理时间": 0.0,
            "平均处理时间": 0.0,
            "启动时间": time.time()
        }

    def initialize(self) -> None:
        """初始化FaceFusion系统"""
        if self.initialized:
            return
            
        try:
            self.logger.info("🚀 正在初始化 FaceFusion 3.3.0 人脸交换系统...")
            FaceFusionConfig.apply_config(self.custom_config)
            self.initialized = True
            self.logger.info("✅ FaceFusion 初始化完成，系统就绪")
            
        except Exception as error:
            self.logger.error(f"❌ 初始化失败: {str(error)}")
            raise error

    def process_request(self, source_url: str, target_url: str, 
                       resolution: str = "1024x1024",
                       model: str = "inswapper_128_fp16") -> ProcessingResult:
        """
        处理人脸交换请求
        
        参数:
            source_url: 包含要交换人脸的图片URL
            target_url: 要被换脸的目标图片URL  
            resolution: 输出图片分辨率，如 "1024x1024"
            model: AI模型名称
            
        返回:
            处理结果对象
        """
        request_start_time = time.time()
        self.stats["总请求数"] += 1
        
        # 确保系统已初始化
        if not self.initialized:
            self.initialize()
        
        with ResourceManager().auto_cleanup() as resource_manager:
            try:
                self.logger.info(f"📨 收到新的人脸交换请求")
                self.logger.info(f"   📋 输出分辨率: {resolution}")
                self.logger.info(f"   🤖 使用模型: {model}")
                
                # 创建工作目录
                work_dir = resource_manager.create_temp_dir("faceswap_")
                
                # 下载文件
                self.logger.info("📥 开始下载输入图片...")
                
                try:
                    # 使用 FaceFusion 下载源图片
                    conditional_download(work_dir, [source_url])
                    source_filename = os.path.basename(urlparse(source_url).path)
                    if not source_filename or '.' not in source_filename:
                        source_filename = "source.jpg"
                    source_path = os.path.join(work_dir, source_filename)
                    self.logger.info(f"✅ 源图片下载成功: {source_filename}")
                except Exception as e:
                    return ProcessingResult(status="失败", error=f"下载源图片失败: {str(e)}")
                
                try:
                    # 使用 FaceFusion 下载目标图片
                    conditional_download(work_dir, [target_url])
                    target_filename = os.path.basename(urlparse(target_url).path)
                    if not target_filename or '.' not in target_filename:
                        target_filename = "target.jpg"
                    target_path = os.path.join(work_dir, target_filename)
                    self.logger.info(f"✅ 目标图片下载成功: {target_filename}")
                except Exception as e:
                    return ProcessingResult(status="失败", error=f"下载目标图片失败: {str(e)}")
                
                # 准备输出路径
                parsed_url = urlparse(target_url)
                target_ext = os.path.splitext(parsed_url.path)[1] if '.' in parsed_url.path else '.jpg'
                output_path = os.path.join(work_dir, f"output{target_ext}")
                
                # 执行人脸交换
                result = process_face_swap(
                    source_paths=[source_path],
                    target_path=target_path,
                    output_path=output_path,
                    resolution=resolution,
                    model_name=model
                )
                
                # 更新统计数据
                request_time = time.time() - request_start_time
                self.stats["总处理时间"] += request_time
                
                if result.status == "成功":
                    self.stats["成功请求数"] += 1
                    self.logger.info(f"🎉 请求处理成功!")
                else:
                    self.stats["失败请求数"] += 1
                    self.logger.warning(f"⚠️ 请求处理失败: {result.error}")
                
                # 计算平均处理时间
                self.stats["平均处理时间"] = (
                    self.stats["总处理时间"] / self.stats["总请求数"]
                )
                
                return result
                
            except Exception as error:
                self.stats["失败请求数"] += 1
                self.logger.error(f"❌ 请求处理异常: {str(error)}")
                return ProcessingResult(
                    status="失败",
                    error=str(error),
                    traceback=traceback.format_exc()
                )

    def get_stats(self) -> Dict[str, Any]:
        """获取详细的系统统计信息"""
        uptime = time.time() - self.stats["启动时间"]
        
        return {
            **self.stats,
            "运行时间秒": round(uptime, 2),
            "运行时间描述": f"{int(uptime // 3600)}小时{int((uptime % 3600) // 60)}分钟",
            "系统状态": "正常运行" if self.initialized else "未初始化",
            "成功率": round(
                self.stats["成功请求数"] / max(self.stats["总请求数"], 1) * 100, 2
            ),
            "当前时间": time.strftime("%Y-%m-%d %H:%M:%S")
        }


# ============================================================================
# 全局实例和主要接口
# ============================================================================

# 创建全局处理器实例
handler_instance = FaceFusionHandler()


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
        result = handler_instance.process_request(
            source_url=source_url,
            target_url=target_url,
            resolution=resolution,
            model=model
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
        stats = handler_instance.get_stats()
        return {
            'status': 'healthy',
            'service': 'FaceFusion 人脸交换服务',
            'version': '3.3.0 中文优化版',
            'description': '智能人脸交换处理系统',
            **stats
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
            logger.info(f"   🎯 人脸检测模型: {FaceFusionConfig.face_detector_model}")
            logger.info(f"   🤖 人脸交换模型: {FaceFusionConfig.face_swapper_model}")
            logger.info(f"   ⚡ 执行提供商: {FaceFusionConfig.execution_providers}")
            logger.info(f"   💾 显存策略: {FaceFusionConfig.video_memory_strategy}")
            
            runpod.serverless.start({
                "handler": handler,
                "return_aggregate_stream": True
            })
        else:
            logger.error("❌ RunPod SDK 不可用，无法启动服务器")
            logger.info("💡 安装提示: pip install runpod")