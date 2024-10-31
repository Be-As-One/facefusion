# FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# ARG FACEFUSION_VERSION=2.6.1
# ENV GRADIO_SERVER_NAME=0.0.0.0

# WORKDIR /facefusion

# RUN apt-get update
# RUN apt-get install python3.10 -y
# RUN apt-get install python-is-python3 -y
# RUN apt-get install pip -y
# RUN apt-get install git -y
# RUN apt-get install curl -y
# RUN apt-get install ffmpeg -y
# RUN apt-get install vim -y

# RUN git clone https://github.com/facefusion/facefusion.git --branch ${FACEFUSION_VERSION} --single-branch .

FROM  harbor.abcfreemusic.com/vegoo/base-image/facefusion-baseimage:v1.0.1
RUN apt update && \
    apt install -y supervisor htop
RUN pip install flask SQLAlchemy pymysql google-cloud-pubsub google-cloud-storage

COPY . .

RUN python install.py --onnxruntime cuda-11.8 --skip-conda

COPY swapper.conf /etc/supervisor/conf.d/swapper.conf

ENV GOOGLE_APPLICATION_CREDENTIALS="/facefusion/auth.json"

EXPOSE 5000

# CMD ["supervisord", "-c", "/etc/supervisor/conf.d/swapper.conf"]
# CMD ["sleep", "infinity"]
CMD ["python", "consumer_start.py"]

# COPY /mnt/disks/t4/facefusion/facefusion/face_analyser.py /facefusion/facefusion/face_analyser.py

# COPY TensorRT-8.6.1.6 /facefusion/TensorRT-8.6.1.6
# 设置 LD_LIBRARY_PATH 环境变量
# ENV LD_LIBRARY_PATH=/facefusion/TensorRT-8.6.1.6/lib:$LD_LIBRARY_PATH

# COPY datasets /facefusion/datasets

# CMD  [ 'python', 'run.py', '--execution-providers', 'cuda' ]
# docker build -t  facefusion261:latest -f Dockerfile .
# docker run -it --name facefusion --rm --gpus all,capabilities=video  facefusion261:latest bash
# export GOOGLE_APPLICATION_CREDENTIALS="/facefusion/auth.json"
# docker run -it --name facefusion --rm --gpus all,capabilities=video -p 7860:7860 -v /mnt/disks/t4/facefusion/datasets:/facefusion/datasets -v storge:/facefusion/.assets  facefusion:2.6.1 bash
# docker run  -it --name facefusion --gpus all,capabilities=video -p  7860:7860   us-central1-docker.pkg.dev/photoart-e9831/api/facefusion261:v1.0.1 bash
# python run.py --execution-providers cuda\

# docker tag facefusion261:latest harbor.abcfreemusic.com/vegoo/model/test/video-faceswap:v1.0.1
# docker push harbor.abcfreemusic.com/vegoo/model/test/video-faceswap:v1.0.1