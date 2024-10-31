import os
import time
import threading
import datetime

class Snowflake:
    """
    Snowflake ID Generator
    Generates unique 64-bit integers based on the Twitter Snowflake algorithm.
    """

    def __init__(self, datacenter_id: int, worker_id: int, epoch: int = 1287187200000):
        """
        Initializes the Snowflake generator.

        :param datacenter_id: ID of the datacenter (0-31)
        :param worker_id: ID of the worker/machine (0-31)
        :param epoch: Custom epoch (in milliseconds). Defaults to 2010-10-16 00:00:00 UTC.
        """
        # Constants
        self.EPOCH = epoch
        
        self.DATACENTER_ID_BITS = 5
        self.WORKER_ID_BITS = 5
        self.SEQUENCE_BITS = 12

        self.MAX_DATACENTER_ID = -1 ^ (-1 << self.DATACENTER_ID_BITS)  # 31
        self.MAX_WORKER_ID = -1 ^ (-1 << self.WORKER_ID_BITS)          # 31
        self.MAX_SEQUENCE = -1 ^ (-1 << self.SEQUENCE_BITS)            # 4095

        self.DATACENTER_ID_SHIFT = self.SEQUENCE_BITS + self.WORKER_ID_BITS
        self.WORKER_ID_SHIFT = self.SEQUENCE_BITS
        self.TIMESTAMP_SHIFT = self.SEQUENCE_BITS + self.WORKER_ID_BITS + self.DATACENTER_ID_BITS

        # Validate IDs
        if datacenter_id > self.MAX_DATACENTER_ID or datacenter_id < 0:
            raise ValueError(f"datacenter_id must be between 0 and {self.MAX_DATACENTER_ID}")
        if worker_id > self.MAX_WORKER_ID or worker_id < 0:
            raise ValueError(f"worker_id must be between 0 and {self.MAX_WORKER_ID}")

        self.datacenter_id = datacenter_id
        self.worker_id = worker_id
        self.sequence = 0
        self.last_timestamp = -1

        # Thread lock for safe multi-threaded access
        self.lock = threading.Lock()

    def _current_time(self) -> int:
        """
        Returns the current time in milliseconds.
        """
        return int(time.time() * 1000)

    def _wait_next_millis(self, last_timestamp: int) -> int:
        """
        Waits until the next millisecond.
        """
        timestamp = self._current_time()
        while timestamp <= last_timestamp:
            timestamp = self._current_time()
        return timestamp

    def generate_id(self) -> int:
        """
        Generates a new unique ID.

        :return: Unique 64-bit integer
        """
        with self.lock:
            timestamp = self._current_time()

            if timestamp < self.last_timestamp:
                # Clock moved backwards. Adjust the timestamp.
                timestamp = self.last_timestamp

            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.MAX_SEQUENCE
                if self.sequence == 0:
                    # Sequence exhausted in this millisecond, wait for next
                    timestamp = self._wait_next_millis(self.last_timestamp)
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            id_ = ((timestamp - self.EPOCH) << self.TIMESTAMP_SHIFT) | \
                  (self.datacenter_id << self.DATACENTER_ID_SHIFT) | \
                  (self.worker_id << self.WORKER_ID_SHIFT) | \
                  self.sequence

            return id_

# 使用环境变量，但提供更有意义的默认值
datacenter_id = int(os.getenv('SNOWFLAKE_DATACENTER_ID', '31'))
worker_id = int(os.getenv('SNOWFLAKE_WORKER_ID', '31'))

generator = Snowflake(datacenter_id=datacenter_id, worker_id=worker_id)

if __name__ == "__main__":
    print(f"Epoch set to: {datetime.datetime.fromtimestamp(generator.EPOCH / 1000, tz=datetime.timezone.utc)}")
    print(f"Datacenter ID: {datacenter_id}, Worker ID: {worker_id}")
    for _ in range(10):
        id_ = generator.generate_id()
        print(f"Generated ID: {id_} (Binary: {bin(id_)})")
        time.sleep(0.1)  # 添加小的延迟以便观察
