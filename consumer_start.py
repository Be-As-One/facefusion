from pubsub.baseconsumer import BaseConsumer
import threading


if __name__ == '__main__':
    consumer = BaseConsumer("facefusion-subscription")
    stop_event = threading.Event()
    try:
        consumer.start_consumer(stop_event)
    except KeyboardInterrupt:
        consumer.shutdown()