from google.cloud import pubsub_v1
from datetime import datetime
from utils.logger import logger
from config.conf import facefusion_topic_name

class Publisher:
    def __init__(self):
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_name = f'projects/photoart-e9831/topics/{facefusion_topic_name}'
        logger.info(f"publisher topic name: {self.topic_name}")

    def publish_messages(self, message):
        try:
            future = self.publisher.publish(self.topic_name, message.encode('utf-8'))
            future.result()  # 等待消息发布完成
            logger.info("publisher add message")
            return True
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            return False

facefusion_publisher = Publisher()

if __name__ == '__main__':
    import json
    # file_paths = [
    #     ["datasets/source.jpg"],
    #     "datasets/debugger.jpeg",
    #     "datasets/debugger-swap.jpeg"
    # ]
    file_paths = [
        ["datasets/source.jpg"],
        "datasets/test.mp4",
        "datasets/test_out.mp4"
    ]
    msg  = {
            "request_id": "0d0cf7061ec147febc645d9bcaf1a0de",
            "facefusion_type": "many",
            "file_paths": file_paths,
            "resolution": "1470x800",
    }
    facefusion_publisher.publish_messages(
        json.dumps(msg)
    )
    # for i in range(10):
    #     current_time = datetime.now().strftime("%Y/%m/%d %H-%M-%S")
    #     data = f'message number {i}, time {current_time}'
    #     Publisher().publish_messages(data)
        # time.sleep(1)  # Wait for 1 second before publishing the next message