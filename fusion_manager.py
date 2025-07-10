#!/usr/bin/env python3
"""
FaceFusion Manager - Core processing logic
Handles FaceFusion initialization and face swap processing
"""

from facefusion.filesystem import is_image, is_video
from facefusion.download import conditional_download
from facefusion.core import conditional_process
from facefusion import state_manager
import os
import sys
import time
import tempfile
import traceback
import shutil
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# FaceFusion imports

# Configure logging
logger = logging.getLogger("FaceFusion-Manager")


# ============================================================================
# Request/Response Models
# ============================================================================

class ProcessRequest:
    """Face swap processing request"""

    def __init__(self, source_url: str, target_url: str, resolution: str = "1024x1024", model: str = "inswapper_128_fp16"):
        self.source_url = source_url
        self.target_url = target_url
        self.resolution = resolution
        self.model = model


class ProcessResponse:
    """Face swap processing response"""

    def __init__(self, status: str, output_path: Optional[str] = None, processing_time: Optional[float] = None, 
                 error: Optional[str] = None, job_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.status = status
        self.output_path = output_path
        self.processing_time = processing_time
        self.error = error
        self.job_id = job_id
        self.metadata = metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format"""
        result = {
            'status': self.status,
            'processing_time': self.processing_time
        }
        
        if self.output_path:
            result['output_path'] = self.output_path
        if self.error:
            result['error'] = self.error
        if self.job_id:
            result['job_id'] = self.job_id
        if self.metadata:
            result['metadata'] = self.metadata
            
        return result


# ============================================================================
# FaceFusion Helper Functions
# ============================================================================

def headless_conditional_process(sources, target, output, resolution, face_swapper_model):
    """Headless processing function using FaceFusion native configuration"""
    # Quick verification that processors are loaded
    processors = state_manager.get_item('processors')
    logger.info(f"Processors: {processors}")
    # Only set request-specific parameters directly, avoiding apply_args
    # which would overwrite INI-loaded config with None values
    state_manager.set_item('source_paths', sources)
    state_manager.set_item('target_path', target)
    state_manager.set_item('output_path', output)
    state_manager.set_item('output_image_resolution', resolution)
    state_manager.set_item('output_video_resolution', resolution)
    if face_swapper_model:
        state_manager.set_item('face_swapper_model', face_swapper_model)
    
    # Debug: Log ALL state manager values after setting request params
    logger.info("=== DEBUG: ALL State Manager Values ===")
    all_keys = [
        # Paths
        'config_path', 'temp_path', 'jobs_path', 'source_paths', 'target_path', 'output_path',
        # Patterns
        'source_pattern', 'target_pattern', 'output_pattern',
        # Face detector
        'face_detector_model', 'face_detector_size', 'face_detector_angles', 'face_detector_score',
        # Face landmarker
        'face_landmarker_model', 'face_landmarker_score',
        # Face selector
        'face_selector_mode', 'face_selector_order', 'face_selector_age_start', 'face_selector_age_end',
        'face_selector_gender', 'face_selector_race', 'reference_face_position', 'reference_face_distance',
        'reference_frame_number',
        # Face masker
        'face_occluder_model', 'face_parser_model', 'face_mask_types', 'face_mask_areas',
        'face_mask_regions', 'face_mask_blur', 'face_mask_padding',
        # Frame extraction
        'trim_frame_start', 'trim_frame_end', 'temp_frame_format', 'keep_temp',
        # Output creation
        'output_image_quality', 'output_image_resolution', 'output_audio_encoder', 'output_audio_quality',
        'output_audio_volume', 'output_video_encoder', 'output_video_preset', 'output_video_quality',
        'output_video_resolution', 'output_video_fps',
        # Processors
        'processors', 'age_modifier_model', 'age_modifier_direction', 'deep_swapper_model',
        'deep_swapper_morph', 'expression_restorer_model', 'expression_restorer_factor',
        'face_debugger_items', 'face_editor_model', 'face_enhancer_model', 'face_enhancer_blend',
        'face_enhancer_weight', 'face_swapper_model', 'face_swapper_pixel_boost', 'frame_colorizer_model',
        'frame_colorizer_size', 'frame_colorizer_blend', 'frame_enhancer_model', 'frame_enhancer_blend',
        'lip_syncer_model', 'lip_syncer_weight',
        # UIs
        'open_browser', 'ui_layouts', 'ui_workflow',
        # Download
        'download_providers', 'download_scope',
        # Benchmark
        'benchmark_resolutions', 'benchmark_cycle_count',
        # Execution
        'execution_device_id', 'execution_providers', 'execution_thread_count', 'execution_queue_count',
        # Memory
        'video_memory_strategy', 'system_memory_limit',
        # Misc
        'log_level', 'halt_on_error',
        # Jobs
        'job_id', 'job_status', 'step_index'
    ]
    
    for key in all_keys:
        value = state_manager.get_item(key)
        if value is not None:
            logger.info(f"{key}: {value}")
    
    # Verify critical configuration is loaded
    processors = state_manager.get_item('processors')
    if not processors:
        raise Exception("Critical error: processors configuration not loaded")
    
    # Process
    error_code = conditional_process()
    return error_code


# ============================================================================
# FaceFusion Manager
# ============================================================================

class FaceFusionManager:
    """Manages FaceFusion initialization and processing"""
    
    def __init__(self):
        self.initialized = False
        
    def initialize(self):
        """Initialize FaceFusion with INI configuration"""
        if self.initialized:
            return
            
        try:
            logger.info("Initializing FaceFusion...")
            
            # Set config path for FaceFusion to use
            config_path = str(PROJECT_ROOT / 'facefusion.ini')
            state_manager.init_item('config_path', config_path)
            
            # Use FaceFusion's native program creation and parsing to load INI configuration
            from facefusion.program import create_program
            from facefusion.args import apply_args
            
            # Create the argument parser program
            program = create_program()
            
            # Parse minimal arguments to trigger config loading
            # This will cause all the create_*_program() functions to read from the INI file
            args = program.parse_args(['headless-run', '--config-path', config_path])
            
            # Convert args to dictionary and apply to state manager
            args_dict = vars(args)
            apply_args(args_dict, state_manager.init_item)
            
            # Verify configuration was loaded correctly
            logger.info("=== Config verification after initialization ===")
            critical_configs = {
                'processors': state_manager.get_item('processors'),
                'face_detector_model': state_manager.get_item('face_detector_model'),
                'face_selector_mode': state_manager.get_item('face_selector_mode'),
                'execution_providers': state_manager.get_item('execution_providers'),
                'face_enhancer_model': state_manager.get_item('face_enhancer_model'),
                'face_enhancer_blend': state_manager.get_item('face_enhancer_blend'),
                'face_enhancer_weight': state_manager.get_item('face_enhancer_weight'),
                'face_swapper_model': state_manager.get_item('face_swapper_model'),
                'face_swapper_pixel_boost': state_manager.get_item('face_swapper_pixel_boost'),
            }
            
            for key, value in critical_configs.items():
                logger.info(f"✅ {key}: {value}")
            
            if not critical_configs['processors']:
                raise Exception("Critical error: processors not loaded from INI config")
            
            self.initialized = True
            logger.info("FaceFusion initialized successfully with INI config")
        except Exception as e:
            logger.error(f"FaceFusion initialization failed: {str(e)}")
            logger.error(traceback.format_exc())
            raise
        
    async def process_face_swap(self, request: ProcessRequest) -> ProcessResponse:
        """Process a face swap request"""
        start_time = time.time()
        job_id = str(uuid.uuid4())[:8]
        temp_dir = tempfile.mkdtemp(prefix="facefusion_")
        
        try:
            logger.info(f"Processing job {job_id}")
            
            # Download source file
            logger.info("Downloading source file...")
            state_manager.set_item('download_providers', ['github', 'huggingface'])
            state_manager.set_item('log_level', 'info')
            
            conditional_download(temp_dir, [request.source_url])
            source_files = os.listdir(temp_dir)
            if not source_files:
                raise FileNotFoundError(f"Failed to download source file from {request.source_url}")
            source_path = os.path.join(temp_dir, source_files[0])
            
            # Download target file
            logger.info("Downloading target file...")
            conditional_download(temp_dir, [request.target_url])
            all_files = os.listdir(temp_dir)
            target_files = [f for f in all_files if f not in source_files]
            if not target_files:
                raise FileNotFoundError(f"Failed to download target file from {request.target_url}")
            target_path = os.path.join(temp_dir, target_files[0])
            
            # Verify files
            if not is_image(source_path):
                raise ValueError(f"Source file is not a valid image: {source_path}")
            if not is_image(target_path) and not is_video(target_path):
                raise ValueError(f"Target file is not a valid image or video: {target_path}")
            
            # Determine output path with correct extension
            target_ext = os.path.splitext(target_path)[1] or '.jpg'
            output_filename = f"{job_id}_output{target_ext}"
            output_path = os.path.join(temp_dir, output_filename)
            
            # Process face swap
            logger.info(f"Starting face swap processing for job {job_id}")
            error_code = headless_conditional_process(
                sources=[source_path],
                target=target_path,
                output=output_path,
                resolution=request.resolution,
                face_swapper_model=request.model
            )
            
            processing_time = time.time() - start_time
            
            if error_code == 0 and os.path.exists(output_path):
                # Copy to outputs directory
                final_output_path = os.path.join(PROJECT_ROOT, "outputs", output_filename)
                os.makedirs(os.path.dirname(final_output_path), exist_ok=True)
                shutil.copy2(output_path, final_output_path)
                
                logger.info(f"Job {job_id} completed successfully in {processing_time:.2f}s")
                
                return ProcessResponse(
                    status="success",
                    output_path=f"/outputs/{output_filename}",
                    processing_time=processing_time,
                    job_id=job_id,
                    metadata={
                        "resolution": request.resolution,
                        "model": request.model,
                        "file_type": "video" if is_video(target_path) else "image"
                    }
                )
            else:
                error_msg = f"Processing failed with error code: {error_code}"
                raise Exception(error_msg)
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            logger.error(f"Job {job_id} failed: {error_msg}")
            logger.error(traceback.format_exc())
            
            return ProcessResponse(
                status="failed",
                error=error_msg,
                processing_time=processing_time,
                job_id=job_id
            )
        finally:
            # Clean up temp directory
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up temp dir: {e}")