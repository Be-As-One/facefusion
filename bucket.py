import os
from google.cloud import storage
from utils.logger import logger
from config.conf import bucket_name
from concurrent.futures import ThreadPoolExecutor
import base64
from io import BytesIO

class GCSUtils:
    def __init__(self):
        if not bucket_name:
            raise ValueError("Bucket name must be provided either as an argument or through the GCS_BUCKET_NAME environment variable.")
        
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.executor = ThreadPoolExecutor(max_workers=4)  # You can adjust the number of workers

    def upload_file(self, source_file_name, destination_blob_name):
        """Uploads a file to the bucket and deletes the local file if upload succeeds."""
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_filename(source_file_name)
            logger.info(f"File {source_file_name} uploaded to {destination_blob_name}.")
            
            # Delete the local file after successful upload
            os.remove(source_file_name)
            logger.info(f"Local file {source_file_name} deleted after successful upload.")

            url = f"https://storage.googleapis.com/{bucket_name}/{destination_blob_name}"
            return True, url
        except Exception as e:
            logger.error(f"Failed to upload file {source_file_name} to {destination_blob_name}: {e}")
            raise e

    def upload_base64(self, base64_data, destination_blob_name):
        """
        上传 base64 编码的数据到 Google Cloud Storage 存储桶，并返回公共 URL。

        :param base64_data: base64 编码的字符串
        :param destination_blob_name: 目标 blob 的名称
        :return: 上传文件的公共 URL
        """
        try:
            # 解码 base64 数据
            file_data = base64.b64decode(base64_data)
            
            # 创建一个 BytesIO 对象
            file_obj = BytesIO(file_data)
            
            # 获取 blob 对象
            blob = self.bucket.blob(destination_blob_name)
            
            # 上传数据
            blob.upload_from_file(file_obj, content_type='application/octet-stream')
            
            # 设置 blob 为公开可访问
            blob.make_public()
            
            # 获取公共 URL
            public_url = blob.public_url
            
            logger.info(f"Base64 data uploaded to {destination_blob_name}. Public URL: {public_url}")
            
            return public_url
        except Exception as e:
            logger.error(f"Failed to upload base64 data to {destination_blob_name}: {e}")
            raise
    
    # 上传二进制图片
    def upload_binary_image(self, binary_data, destination_blob_name):
        """
        上传二进制图片数据到 Google Cloud Storage 存储桶，并返回公共 URL。

        :param binary_data: 二进制图片数据
        :param destination_blob_name: 目标 blob 的名称
        :return: 上传文件的公共 URL
        """
        try:
            # 创建一个 BytesIO 对象
            file_obj = BytesIO(binary_data)
            
            # 获取 blob 对象
            blob = self.bucket.blob(destination_blob_name)
            
            # 上传数据
            blob.upload_from_file(file_obj, content_type='image/png')  # 假设是 PNG 格式，可以根据实际情况调整
            
            # 设置 blob 为公开可访问
            blob.make_public()
            
            # 获取公共 URL
            public_url = blob.public_url
            
            logger.info(f"Binary image uploaded to {destination_blob_name}. Public URL: {public_url}")
            
            return public_url
        except Exception as e:
            logger.error(f"Failed to upload binary image to {destination_blob_name}: {e}")
            raise

    def upload_file_async(self, source_file_name, destination_blob_name):
        """Starts a background thread to upload a file."""
        future = self.executor.submit(self.upload_file, source_file_name, destination_blob_name)
        return future

gcs_utils = GCSUtils()


if __name__ == "__main__":
    import time
    try:
        t0 = time.time()
        future = gcs_utils.upload_file_async("1.png", "output/11/08/1.png")
        t1 = time.time()
        print(f"Upload initiated, time taken to start: {t1 - t0}")
        
        # Optionally wait for the upload to complete
        future.result()
        print("Upload completed.")
    except Exception as e:
        logger.error(f"An error occurred: {e}")

    # Optionally wait for all background tasks to complete
    gcs_utils.executor.shutdown(wait=True)
    print("All background tasks completed.")

