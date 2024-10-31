import os

env_project_id = os.getenv('PROJECT_ID', 'photoart-e9831')
# pubsub config
app_env = os.getenv('APP_ENV', 'dev') # dev, test, prod
if app_env in ['dev']:
    bucket_name = os.getenv('BUCKET_NAME', 'mtask_storage')
    sub_path = os.getenv('SUB_PATH', 'test')
    facefusion_topic_name = os.getenv('FACEFUSION_TOPIC_NAME', 'mtask-video-faceswap-test')
    facefusion_subscription_name = os.getenv('FACEFUSION_SUBSCRIPTION_NAME', 'mtask-video-faceswap-test-sub')
    project_name = os.getenv('PROJECT_NAME', 'data')
    base_url = os.getenv('BASE_URL', 'http://35.190.80.13')
    mysql_db_url = os.getenv('MYSQL_DATABASE_URL', r"mysql+pymysql://admin:CKBN\~3)1?{xQ1Z:@35.223.61.68:3306/aipic-test")
elif app_env in ['test']:
    bucket_name = os.getenv('BUCKET_NAME', 'mtask_storage')
    sub_path = os.getenv('SUB_PATH', 'test')
    facefusion_topic_name = os.getenv('FACEFUSION_TOPIC_NAME', 'mtask-video-faceswap-test')
    facefusion_subscription_name = os.getenv('FACEFUSION_SUBSCRIPTION_NAME', 'mtask-video-faceswap-test-sub')
    project_name = os.getenv('PROJECT_NAME', 'testdata')
    base_url = os.getenv('BASE_URL', 'http://35.190.80.13')
    mysql_db_url = os.getenv('MYSQL_DATABASE_URL', r"mysql+pymysql://admin:CKBN\~3)1?{xQ1Z:@10.109.48.3:3306/aipic-test")
elif app_env in ['prod', 'production']:
    bucket_name = os.getenv('BUCKET_NAME', 'mtask_storage')
    sub_path = os.getenv('SUB_PATH', 'video-faceswap')
    facefusion_topic_name = os.getenv('FACEFUSION_TOPIC_NAME', 'facefusion')
    facefusion_subscription_name = os.getenv('FACEFUSION_SUBSCRIPTION_NAME', 'facefusion-sub')
    project_name = os.getenv('PROJECT_NAME', 'data')
    base_url = os.getenv('BASE_URL', 'http://10.0.0.120')
    mysql_db_url = os.getenv('MYSQL_DATABASE_URL', r"mysql+pymysql://admin:CKBN\~3)1?{xQ1Z:@10.109.48.3:3306/aipic-test")
else:
    raise ValueError(f"Invalid APP_ENV: {app_env}")

# face detect config
env_expanded_face_scale = float(os.environ.get('EXPANDED_FACE_SCALE', 1.2))
env_threshold_qs1 = float(os.environ.get('THRESHOLD_QS1', 0.65))
env_threshold_qs2 = float(os.environ.get('THRESHOLD_QS2', 0.75))
env_target_id = int(os.environ.get('TARGET_ID', 6))
env_thresho_id = int(os.environ.get('THRESHO_ID', 0.2))
env_draw_faces_cache_max = int(os.environ.get('DRAW_FACES_CACHE_MAX', 80))

# common consumer config
max_file_size = int(os.getenv('MAX_SIZE', 500 * 1024 * 1024))  # 500 MB in bytes
max_duration = int(os.getenv('MAX_DURATION', 600))  # 10 minutes in seconds
message_timeout = int(os.getenv('MESSAGE_TIMEOUT', 3600))  # 1 hour in seconds
conn_retry_interval = int(os.getenv('CONN_RETRY_INTERVAL', 5)) # 5 seconds
ack_deadline_seconds = int(os.getenv('ACK_DEADLINE_SECONDS', max_duration))

# gcs
bucket_name = os.getenv('BUCKET_NAME', 'aivideo_faceswap_storage')
env_gcs_bucket_url = os.getenv('GCS_BUCKET_URL', f"https://storage.googleapis.com/{bucket_name}/")


# ffmpeg 
env_max_video_size = int(os.environ.get('MAX_VIDEO_SIZE', 1280))
env_min_video_size = int(os.environ.get('MIN_VIDEO_SIZE', 300))
env_max_image_size = int(os.environ.get('MAX_IMAGE_SIZE', 4000))
env_min_image_size = int(os.environ.get('MIN_IMAGE_SIZE', 300))

# service name
service = os.getenv('SERVICE', 'video-faceswap')


"""
异步队列-生产	异步队列-测试
mtask-file-detect	mtask-file-detect-test
mtask-video-faceswap	mtask-video-faceswap-test
mtask-comfy-mix	mtask-comfy-mix-test
mtask-comfy-repaint	mtask-comfy-repaint-test
mtask-comfy-baby	mtask-comfy-baby-test
mtask-comfy-diylab	mtask-comfy-diylab-test

"""