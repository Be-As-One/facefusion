FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

ARG FACEFUSION_VERSION=2.6.1
ENV GRADIO_SERVER_NAME=0.0.0.0

WORKDIR /facefusion

RUN apt-get update
RUN apt-get install python3.10 -y
RUN apt-get install python-is-python3 -y
RUN apt-get install pip -y
RUN apt-get install git -y
RUN apt-get install curl -y
RUN apt-get install ffmpeg -y
RUN apt-get install vim -y

COPY .assets /facefusion/.assets
COPY datasets /facefusion/datasets
# COPY TensorRT-8.6.1.6 /facefusion/TensorRT-8.6.1.6
# ENV LD_LIBRARY_PATH=/facefusion/TensorRT-8.6.1.6/lib:$LD_LIBRARY_PATH


# docker build -t facefusion-baseimage:latest -f base.Dockerfile .
# docker run -it --rm --gpus all,capabilities=video facefusion-baseimage:latest bash
# docker tag facefusion-baseimage:latest us-central1-docker.pkg.dev/photoart-e9831/base-image/facefusion-baseimage:v1.0.0
# docker push us-central1-docker.pkg.dev/photoart-e9831/base-image/facefusion-baseimage:v1.0.0