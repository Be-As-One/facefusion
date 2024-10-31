import time
from functools import wraps
from utils.logger import logger

def timing_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()  # 记录开始时间
        result = func(*args, **kwargs)  # 执行被装饰的函数
        end_time = time.time()  # 记录结束时间
        execution_time = end_time - start_time  # 计算执行时间
        logger.info(f"-----------> Function '{func.__name__}' executed in {execution_time:.4f} seconds")
        return result
    return wrapper