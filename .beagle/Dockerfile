ARG BASE=debian:bookworm-slim

# 编译阶段
FROM python:3.11-bookworm AS builder

WORKDIR /build
COPY . .

RUN pip install \
      -i https://pypi.tuna.tsinghua.edu.cn/simple \
      --upgrade pip pyinstaller \
    && pip install \
      -i https://pypi.tuna.tsinghua.edu.cn/simple \
      -r requirements.txt \
    && pip install \
      -i https://pypi.tuna.tsinghua.edu.cn/simple \
      --no-deps face_recognition \
    && pyinstaller \
      -D Movie_Data_Capture.py \
      --python-option u \
      --noconfirm \
      --hidden-import "ImageProcessing.cnn" \
      --add-data "$(python -c 'import cloudscraper as _; print(_.__path__[0])' | tail -n 1):cloudscraper" \
      --add-data "$(python -c 'import opencc as _; print(_.__path__[0])' | tail -n 1):opencc" \
      --add-data "$(python -c 'import face_recognition_models as _; print(_.__path__[0])' | tail -n 1):face_recognition_models" \
      --add-data "Img:Img" \
      --add-data "scrapinglib:scrapinglib" \
    && cp ./config.ini ./dist/Movie_Data_Capture/config.template

# 运行阶段
FROM $BASE

LABEL maintainer="VergilGao"
LABEL build_from="https://github.com/yoshiko2/Movie_Data_Capture"
LABEL org.opencontainers.image.source="https://github.com/VergilGao/docker-mdc"

ENV TZ="Asia/Shanghai"
ENV UID=1000
ENV GID=1000
ENV UMASK=002

ADD .beagle/docker-entrypoint.sh docker-entrypoint.sh

RUN \
    apt-get -y update && apt-get -y upgrade \
    && apt install -y -q \
        gosu \
    && apt-get autoremove --purge -y \
    && apt-get clean -y \
    && chmod +x docker-entrypoint.sh \
    && mkdir -p /data /config \
    && useradd -d /config -s /bin/sh mdc \
    && chown -R mdc /data /config

COPY --from=builder /build/dist/Movie_Data_Capture /app

VOLUME [ "/data", "/config" ]

ENTRYPOINT ["/docker-entrypoint.sh"]
