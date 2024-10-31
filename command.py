import subprocess
from utils.logger import logger
import time

def run_command(source, target, output):
    t0 = time.time()
    # 定义命令和参数
    command = [
        'python', 'run.py',
        '--frame-processors', 'face_swapper', 'face_enhancer',
        '-s', source,
        '-t', target,
        '-o', output,
        '--headless',
        '--face-mask-types', 'occlusion', 'box',
        '--execution-providers', 'cuda'
    ]
    
    # 使用 subprocess.Popen 执行命令并实时读取标准错误
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # 持续读取标准错误
    while True:
        error_output = process.stderr.readline()
        if error_output == '' and process.poll() is not None:
            break
        if error_output:
            logger.error(error_output.strip())  # 只记录标准错误
    
    return_code = process.poll()
    logger.info(f"Process finished with return code: {return_code}")
    t1 = time.time()
    logger.info(f"----------> Time taken: {t1 - t0}")

if __name__ == "__main__":
    run_command('datasets/source.jpg', 'datasets/9s.mp4','datasets/9999s.mp4')

            # if media_type == 'image':
        #     run_command(
        #         file_paths[0][0],
        #         file_paths[1],
        #         file_paths[2],
        #     )
        #     path  = file_paths[2]
        # elif media_type == 'video':
        #     run_command(
        #         file_paths[0][0],
        #         file_paths[1],
        #         file_paths[2],
        #     )
        #     path  = file_paths[2]
        # else:
        #     raise ValueError(f"Invalid media type: {media_type}")   
