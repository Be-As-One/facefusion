import logging
import os
from datetime import datetime, timedelta, timezone

class CSTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        # 设置中国标准时间的时区
        cst_tz = timezone(timedelta(hours=8))
        ct = datetime.fromtimestamp(record.created, tz=cst_tz)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = "%s,%03d" % (t, record.msecs)
        return s

def configure_logging():
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    formatter = CSTFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logging.basicConfig(
        level=log_level,
        handlers=[handler]
    )

# 配置日志
configure_logging()

# 创建 logger 对象
logger = logging.getLogger(__name__)