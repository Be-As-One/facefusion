import subprocess
import json
import os
import imghdr
import math
from utils.logger import logger
from PIL import Image
from config.conf import max_file_size, max_duration, env_max_video_size,env_max_image_size, env_min_image_size, env_min_video_size

import tempfile
import shutil

def combine_video_audio(swap_tmp_path, target_audio_path, output_file):
    if os.path.exists(target_audio_path):
        cmd = [
            'ffmpeg', '-y',
            '-loglevel', 'error',
            '-hwaccel', 'cuda',  # 使用CUDA进行硬件加速
            '-i', swap_tmp_path,
            '-i', target_audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-fflags', '+genpts',
            '-r', '30',
            '-movflags', '+faststart',
            output_file
        ]
    else:
        cmd = [
            'ffmpeg', '-y',
            '-loglevel', 'error',
            '-hwaccel', 'cuda',  # 使用CUDA进行硬件加速
            '-i', swap_tmp_path,
            '-c:v', 'copy',
            '-fflags', '+genpts',
            '-r', '30',
            '-movflags', '+faststart',
            output_file
        ]
    
    subprocess.run(cmd, check=True)

def extract_audio(input_video, output_audio):
    cmd = [
        'ffmpeg', 
        '-loglevel', 'error',  # 或者 quiet 'error' 仅显示错误
        '-hwaccel', 'cuda',  # 使用CUDA进行硬件加速
        '-i', input_video,
        '-vn', '-acodec', 'libmp3lame', '-b:a', '192k',
        output_audio
    ]
    subprocess.run(cmd, check=True)

def get_video_info(video_path):
    # 获取视频流信息
    video_cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=codec_type,width,height,r_frame_rate,codec_name',
        '-show_entries', 'format=duration,size',
        '-of', 'json', video_path
    ]
    video_result = subprocess.run(video_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    video_info = json.loads(video_result.stdout)

    # 获取音频流信息
    audio_cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'a:0',
        '-show_entries', 'stream=codec_type,codec_name',
        '-of', 'json', video_path
    ]
    audio_result = subprocess.run(audio_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    audio_info = json.loads(audio_result.stdout)

    # 合并视频和音频信息
    if 'streams' not in video_info:
        video_info['streams'] = []
    if 'streams' in audio_info:
        video_info['streams'].extend(audio_info['streams'])

    return video_info

def is_image(file_path):
    return imghdr.what(file_path) is not None

def is_gif(file_path):
    return imghdr.what(file_path) == 'gif'

def scale_video(input_file, width, height, bitrate='3M', preset='fast'):
    try:
        # 生成临时输出文件路径
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
            temp_output_file = temp_file.name
        
        cmd = [
            'ffmpeg', '-y',
            '-loglevel', 'error',
            '-hwaccel', 'cuda',  # 使用CUDA进行硬件加速
            '-i', input_file,
            '-vf', f'scale=w={width}:h={height}',  # 使用NPP进行缩放
            '-c:v', 'h264_nvenc',  # 使用NVENC编码器
            '-b:v', bitrate,  # 设置比特率
            '-preset', preset,  # 设置编码预设
            '-c:a', 'copy',
            temp_output_file
        ]
        
        logger.info(f"Scaling video {input_file} to {width}x{height} with bitrate {bitrate} and preset {preset}")
        result = subprocess.run(cmd, check=True)
        
        if result.returncode == 0:
            # 使用shutil.move替换原始文件
            shutil.move(temp_output_file, input_file)
            logger.info(f"Video scaled and saved to {input_file}")
        else:
            raise subprocess.CalledProcessError(result.returncode, cmd)
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Error scaling video: {e}", exc_info=True)
        # 如果处理失败，删除临时文件
        if os.path.exists(temp_output_file):
            os.remove(temp_output_file)
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        # 如果处理失败，删除临时文件
        if os.path.exists(temp_output_file):
            os.remove(temp_output_file)
        raise e

def get_file_info(file_path):
    try:
        if not os.path.exists(file_path):
            raise ValueError("File does not exist")

        if is_image(file_path):
            logger.info("Extracting image...")
            img = Image.open(file_path)
            aspect_ratio = img.width / img.height
            if aspect_ratio > 21/9 or aspect_ratio < 9/21:
                raise ValueError("不支持的长宽比,最大不超过21:9或者9:21")
            
            # 如果图片尺寸3840x2160以上，缩小到1920x1080
            if img.width > env_max_image_size or img.height > env_max_image_size:
                img.thumbnail((env_max_image_size, env_max_image_size))
                img.save(file_path)
                logger.info(f"Image scaled to {img.width}x{img.height}")
            if img.width < env_min_image_size or img.height < env_min_image_size:
                raise ValueError("图片尺寸太小")

            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                background.save(file_path, "JPEG")
                logger.info(f"Image saved as JPEG: {file_path}")
            
            file_size = os.path.getsize(file_path)
            _file_size = math.floor(file_size / 1024)
            file_info = {
                "width": img.width,
                "height": img.height,
                "duration": 0,
                "r_frame_rate": "0/0",
                "codec_type": "Image",
                "file_size": _file_size
            }
            return "Image", "jpeg", file_info, False

        video_info = get_video_info(file_path)
        logger.info(f"-------> Video info: {video_info.get('streams', [])} - {video_info.get('format', {})}")
        if 'streams' in video_info and len(video_info['streams']) > 0:
            streams = video_info['streams']
            video_stream = next((stream for stream in streams if stream.get('codec_type') == 'video'), None)
            audio_stream = next((stream for stream in streams if stream.get('codec_type') == 'audio'), None)
            
            if video_stream:
                format_info = video_info.get('format', {})
                file_size = float(format_info.get('size', 0))
                duration = float(format_info.get('duration', 0))
                
                if duration > max_duration:
                    raise ValueError("视频时长超过10分钟")
                if file_size > max_file_size:
                    raise ValueError("视频文件大小超过500MB")

                
                width = video_stream.get('width', 0)
                height = video_stream.get('height', 0)
                aspect_ratio = width / height

                if aspect_ratio > 21/9 or aspect_ratio < 9/21:
                    raise ValueError("不支持的长宽比,最大不超过21:9或者9:21")

                if width > env_max_video_size or height > env_max_video_size:
                    new_width, new_height = env_max_video_size, int(env_max_video_size / aspect_ratio)
                    if new_height > env_max_video_size:
                        new_height = env_max_video_size
                        new_width = int(env_max_video_size * aspect_ratio)
                    scale_video(file_path, new_width, new_height)
                    logger.info(f"Video scaled to {new_width}x{new_height}")

                if width < env_min_video_size or height < env_min_video_size:
                    raise ValueError("视频尺寸太小")

                video_stream['file_size'] = math.floor(file_size / 1024)  # KB
                video_stream['duration'] = math.floor(duration)
                
                codec_name = video_stream.get('codec_name', '')
                return "Video", codec_name, video_stream, audio_stream is not None
            else:
                raise ValueError("No video stream found in the file")
        else:
            raise ValueError("invalid video file")
    except Exception as e:
        logger.error(f"Error checking file info: {e}", exc_info=True)
        raise e


if __name__ == '__main__':
    video_path = "1080.mp4"
    print(is_image(video_path))
    media_type, codec_name, info, have_audio = get_file_info(video_path)
    print(media_type, codec_name, info, have_audio)
