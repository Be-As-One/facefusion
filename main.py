import logging
from facefusion.core import cli, conditional_process
import facefusion.globals
import time

logger = logging.getLogger(__name__)

class ModelSwapper:
    def __init__(self, ) -> None:
        cli(is_server=True)
        logger.info(f"==============> facefusion.globals.execution_providers: {facefusion.globals.execution_providers}" )
        facefusion.globals.output_video_encoder = "h264_nvenc"
        logger.info(f"==============> facefusion.globals.output_video_encoder: {facefusion.globals.output_video_encoder}")


    def process(self, sources, target, output, output_image_resolution) -> None:
        """
        sources list of paths to source images
        target path to target image
        output path to output image
        """
        facefusion.globals.source_paths = sources
        facefusion.globals.target_path = target
        facefusion.globals.output_path = output
        facefusion.globals.output_image_resolution = output_image_resolution
        facefusion.globals.output_video_resolution = output_image_resolution
        facefusion.globals.output_video_fps = 30
        facefusion.globals.face_selector_mode = "many"
        
        try:
            conditional_process()
            return output
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            raise e



if __name__ == "__main__":
    import time
    model_swapper = ModelSwapper()
    t0 = time.time()
    model_swapper.process(
        sources=["/mnt/disks/t4/facefusion/datasets/source.jpg"],
        target="/mnt/disks/t4/facefusion/datasets/resized_debugger.jpeg",
        output="/mnt/disks/t4/facefusion/datasets/face-swap78.jpg",
        output_image_resolution="1470x800"
    )
    t1 = time.time()
    print("Time taken:", t1 - t0)
    model_swapper.process(
        sources=["/mnt/disks/t4/facefusion/datasets/source.jpg"],
        target="/mnt/disks/t4/facefusion/datasets/resized_debugger.jpeg",
        output="/mnt/disks/t4/facefusion/datasets/face-swap79.jpg",
        output_image_resolution="1470x800"
    )
    t2 = time.time()
    print("Time taken:", t2 - t1)
    # model_swapper.process(
    #     sources=["/mnt/disks/t4/facefusion/datasets/source.jpg"],
    #     target="/mnt/disks/t4/facefusion/datasets/9s.mp4",
    #     output="/mnt/disks/t4/facefusion/datasets/face-swap-9s-cpu.jpg",
    #     output_image_resolution="720x1280"
    # )
    # t3 = time.time()
    # print("Time taken:", t3 - t2)


# ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 your_video_file.mp4
# ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 your_image_file.jpg

