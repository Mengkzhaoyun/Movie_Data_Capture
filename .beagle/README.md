# Movie_Data_Capture

https://github.com/yoshiko2/Movie_Data_Capture

```bash
git remote add upstream git@github.com:yoshiko2/Movie_Data_Capture.git

git fetch upstream

git merge 6.6.7
```

## dlib

```bash
docker build \
-f .beagle/dlib.Dockerfile \
--build-arg BASE=registry.cn-qingdao.aliyuncs.com/wod/python:v3.11 \
-t docker.io/mengkzhaoyun/movie_data_capture:dlib-19.24.2 \
.
```

## build

```bash
# prepare dlib
rm -rf dist && \
docker run -it --rm \
-v $PWD/:/tmp/dlib/output \
docker.io/mengkzhaoyun/movie_data_capture:dlib-19.24.2 \
cp -r /tmp/dlib/dist /tmp/dlib/output

# build x86
docker run -it --rm \
-v $PWD/:$PWD/ \
-w $PWD/ \
registry.cn-qingdao.aliyuncs.com/wod/python:v3.11 \
bash .beagle/build.sh

# build arm64
rm -rf .venv && \
docker run -it --rm \
-v $PWD/:$PWD/ \
-w $PWD/ \
registry.cn-qingdao.aliyuncs.com/wod/python:v3.11-arm64 \
bash .beagle/build.sh
```

## images

```bash
docker run -it --rm \
-v $PWD/:$PWD/ \
-w $PWD/ \
registry.cn-qingdao.aliyuncs.com/wod/python:v3.11 \
bash .beagle/build.sh && \
docker build \
-f .beagle/Dockerfile \
--build-arg BASE=registry.cn-qingdao.aliyuncs.com/wod/debian:bookworm-slim \
-t docker.io/mengkzhaoyun/movie_data_capture:6.6.10 \
. && \
docker push docker.io/mengkzhaoyun/movie_data_capture:6.6.10
```

## Otel

```bash
# install
bash .venv/bin/activate
.venv/bin/pip3 install opentelemetry-distro opentelemetry-exporter-otlp -i https://pypi.tuna.tsinghua.edu.cn/simple
.venv/bin/opentelemetry-bootstrap -a install

# start
OTEL_SERVICE_NAME=Movie_Data_Capture \
OTEL_TRACES_EXPORTER=otlp \
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger.beagle-devops:4318 \
OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf \
.venv/bin/opentelemetry-instrument \
.venv/bin/python Movie_Data_Capture.py
```
