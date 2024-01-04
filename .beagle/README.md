# Movie_Data_Capture

## debug

```bash
python3 -m venv .venv

source .venv/bin/activate

pip install \
  -i https://pypi.tuna.tsinghua.edu.cn/simple \
  -r requirements.txt
```

## build

```bash
# build x86
docker run -it --rm \
-v $PWD/:/go/src/github.com/mengkzhaoyun/movie_data_capture \
-w /go/src/github.com/mengkzhaoyun/movie_data_capture \
registry.cn-qingdao.aliyuncs.com/wod/python:v3.11-amd64 \
bash .beagle/build.sh

# build arm64
docker run -it --rm \
-v $PWD/:/go/src/github.com/mengkzhaoyun/movie_data_capture \
-w /go/src/github.com/mengkzhaoyun/movie_data_capture \
registry.cn-qingdao.aliyuncs.com/wod/python:v3.11-arm64 \
bash .beagle/build.sh
```

## git

<https://github.com/yoshiko2/Movie_Data_Capture>

```bash
git remote add upstream git@github.com:yoshiko2/Movie_Data_Capture.git

git fetch upstream

git merge 6.6.7
```

## dlib

```bash
# x86
docker build \
-f .beagle/dlib.Dockerfile \
--build-arg BASE=registry.cn-qingdao.aliyuncs.com/wod/python:v3.11-amd64 \
-t registry-vpc.cn-qingdao.aliyuncs.com/wod/movie_data_capture:dlib-19.24.2-amd64 \
. && \
docker push registry-vpc.cn-qingdao.aliyuncs.com/wod/movie_data_capture:dlib-19.24.2-amd64

rm -rf dist/dlib_bin*linux_x86_64.whl && \
docker run -it --rm \
-v $PWD/:/output \
registry-vpc.cn-qingdao.aliyuncs.com/wod/movie_data_capture:dlib-19.24.2-amd64 \
cp -r /tmp/dlib/dist /output

# arm64
docker build \
-f .beagle/dlib.Dockerfile \
--build-arg BASE=registry.cn-qingdao.aliyuncs.com/wod/python:v3.11-arm64 \
-t registry-vpc.cn-qingdao.aliyuncs.com/wod/movie_data_capture:dlib-19.24.2-arm64 \
. && \
docker push registry-vpc.cn-qingdao.aliyuncs.com/wod/movie_data_capture:dlib-19.24.2-arm64

rm -rf dist/dlib_bin*linux_aarch64.whl && \
docker run -it --rm \
-v $PWD/:/output \
registry-vpc.cn-qingdao.aliyuncs.com/wod/movie_data_capture:dlib-19.24.2-arm64 \
cp -r /tmp/dlib/dist /output
```

## Otel

```bash
# install
source .venv/bin/activate
pip install \
  -i https://pypi.tuna.tsinghua.edu.cn/simple \
  opentelemetry-distro \
  opentelemetry-exporter-otlp 
opentelemetry-bootstrap -a install

# start
OTEL_SERVICE_NAME=Movie_Data_Capture \
OTEL_TRACES_EXPORTER=otlp \
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger.beagle-devops:4318 \
OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf \
opentelemetry-instrument \
python Movie_Data_Capture.py
```

## cache

```bash
# 构建缓存-->推送缓存至服务器
docker run --rm \
  -e PLUGIN_REBUILD=true \
  -e PLUGIN_ENDPOINT=$PLUGIN_ENDPOINT \
  -e PLUGIN_ACCESS_KEY=$PLUGIN_ACCESS_KEY \
  -e PLUGIN_SECRET_KEY=$PLUGIN_SECRET_KEY \
  -e DRONE_REPO_OWNER="Mengkzhaoyun" \
  -e DRONE_REPO_NAME="Movie_Data_Capture" \
  -e PLUGIN_MOUNT="./.git,./.python" \
  -v $(pwd):$(pwd) \
  -w $(pwd) \
  registry.cn-qingdao.aliyuncs.com/wod/devops-s3-cache:1.0

# 读取缓存-->将缓存从服务器拉取到本地
docker run --rm \
  -e PLUGIN_RESTORE=true \
  -e PLUGIN_ENDPOINT=$PLUGIN_ENDPOINT \
  -e PLUGIN_ACCESS_KEY=$PLUGIN_ACCESS_KEY \
  -e PLUGIN_SECRET_KEY=$PLUGIN_SECRET_KEY \
  -e DRONE_REPO_OWNER="Mengkzhaoyun" \
  -e DRONE_REPO_NAME="Movie_Data_Capture" \
  -v $(pwd):$(pwd) \
  -w $(pwd) \
  registry.cn-qingdao.aliyuncs.com/wod/devops-s3-cache:1.0
```
