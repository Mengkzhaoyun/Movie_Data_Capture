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
--build-arg BASE=registry.cn-qingdao.aliyuncs.com/wod/python:v3.10 \
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

# build
docker run -it --rm \
-v $PWD/:/docker/src/github.com/mengkzhaoyun/Movie_Data_Capture \
-w /docker/src/github.com/mengkzhaoyun/Movie_Data_Capture \
registry.cn-qingdao.aliyuncs.com/wod/python:v3.10 \
bash .beagle/build.sh
```

## images

```bash
docker build \
-f .beagle/Dockerfile \
--build-arg BASE=registry.cn-qingdao.aliyuncs.com/wod/debian:bullseye-slim \
-t docker.io/mengkzhaoyun/movie_data_capture:6.6.8 \
.

docker push docker.io/mengkzhaoyun/movie_data_capture:6.6.8
```
