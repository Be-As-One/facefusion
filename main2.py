import logging
from facefusion.core import cli, conditional_process
import facefusion.globals
import time
import os
import subprocess
import shutil
import tempfile


logger = logging.getLogger(__name__)


def convert_mp4(input_mp4, output_file, conversion_type, **kwargs):
    """
    通用的 MP4 转换函数。

    参数:
    - input_mp4: 输入的 MP4 文件路径。
    - output_file: 输出文件路径。
    - conversion_type: 转换类型 ('gif' 或 'webp')。
    - kwargs: 其他可选参数（如 fps, lossless, compression_level, quality, loop 等）。

    返回:
    - None
    """
    if not os.path.exists(input_mp4):
        logger.error(f"Input file does not exist: {input_mp4}")
        return

    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        t0 = time.time()
        
        # 生成临时输出文件路径
        suffix = f".{conversion_type}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_output_file = temp_file.name

        if conversion_type == 'gif':
            cmd = [
                'ffmpeg', '-y',
                '-loglevel', 'error',
                '-i', input_mp4,
                '-vf', 'fps=10,scale=320:-1:flags=lanczos',
                '-loop', '0',
                temp_output_file
            ]
        elif conversion_type == 'webp':
            fps = kwargs.get('fps', 10)
            lossless = kwargs.get('lossless', 0)
            compression_level = kwargs.get('compression_level', 4)
            quality = kwargs.get('quality', 70)
            loop = kwargs.get('loop', 0)
            cmd = [
                'ffmpeg', '-y',
                '-loglevel', 'error',
                '-i', input_mp4,
                '-vf', f"fps={fps}",
                '-c:v', 'libwebp',
                '-lossless', str(lossless),
                '-compression_level', str(compression_level),
                '-q:v', str(quality),
                '-loop', str(loop),
                temp_output_file
            ]
        else:
            logger.error(f"Unsupported conversion type: {conversion_type}")
            raise ValueError(f"Unsupported conversion type: {conversion_type}")

        logger.info(f"Converting MP4 {input_mp4} to {conversion_type.upper()}, output to {temp_output_file}")
        result = subprocess.run(cmd, check=True)

        if result.returncode == 0:
            shutil.move(temp_output_file, output_file)
            logger.info(f"MP4 converted and saved to {output_file}")
        else:
            raise subprocess.CalledProcessError(result.returncode, cmd)
        
        t1 = time.time()
        logger.info(f"MP4 to {conversion_type.upper()} conversion total time: {t1 - t0:.2f}s")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting MP4 to {conversion_type.upper()}: {e}", exc_info=True)
        if os.path.exists(temp_output_file):
            os.remove(temp_output_file)
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        if os.path.exists(temp_output_file):
            os.remove(temp_output_file)
        raise e

class ModelSwapper:
    def __init__(self, ) -> None:
        cli(is_server=True)
        logger.info(f"==============> facefusion.globals.execution_providers: {facefusion.globals.execution_providers}" )
        # facefusion.globals.output_video_encoder = "h264_nvenc"
        logger.info(f"==============> facefusion.globals.output_video_encoder: {facefusion.globals.output_video_encoder}")


    def process(self, sources, target, output, resolution) -> None:
        """
        sources list of paths to source images
        target path to target image
        output path to output image
        """
        facefusion.globals.source_paths = sources
        facefusion.globals.target_path = target
        facefusion.globals.output_path = output
        facefusion.globals.output_image_resolution = resolution
        facefusion.globals.output_video_resolution = resolution
        # facefusion.globals.output_video_fps = 30
        # facefusion.globals.face_selector_mode = "many"

        try:
            conditional_process()
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            raise e


if __name__ == "__main__":
    import time
    model_swapper = ModelSwapper()
    t0 = time.time()
    model_swapper.process(
        sources=["/facefusion/datasets/source.jpg"],
        target="/facefusion/datasets/resized_debugger.jpeg",
        output="/facefusion/datasets/face-swap798.jpg",
        resolution="1470x800"
    )
    t1 = time.time()
    print("Time taken:", t1 - t0)
    model_swapper.process(
        sources=["/facefusion/datasets/source.jpg"],
        target="/facefusion/datasets/resized_debugger.jpeg",
        output="/facefusion/datasets/face-swap799.jpg",
        resolution="1470x800"
    )
    t2 = time.time()
    print("Time taken:", t2 - t1)
    # model_swapper.process(
    #     sources=["/facefusion/datasets/source.jpg"],
    #     target="/facefusion/datasets/9s.mp4",
    #     output="/facefusion/datasets/face-swap-9s-cpu.jpg",
    #     output_image_resolution="720x1280"
    # )
    # t3 = time.time()
    # print("Time taken:", t3 - t2)


# ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 your_video_file.mp4
# ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 your_image_file.jpg

