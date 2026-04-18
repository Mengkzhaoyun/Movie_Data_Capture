# Movie_Data_Capture

## debug

> 本地调试使用清华源加速，CI/CD 流水线使用默认 PyPI 源。

```powershell
python -m venv .venv; .venv\Scripts\pip.exe install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

```powershell
echo "" | .venv\Scripts\python.exe src/main.py
```

## build

```bash
# build amd64
docker run -it --rm \
  -v $PWD/:/go/src/github.com/mengkzhaoyun/movie_data_capture \
  -w /go/src/github.com/mengkzhaoyun/movie_data_capture \
  registry.cn-qingdao.aliyuncs.com/wod/python:v3.12-amd64 \
  bash scripts/build.sh

# build arm64
docker run -it --rm \
  -v $PWD/:/go/src/github.com/mengkzhaoyun/movie_data_capture \
  -w /go/src/github.com/mengkzhaoyun/movie_data_capture \
  registry.cn-qingdao.aliyuncs.com/wod/python:v3.12-arm64 \
  bash scripts/build.sh
```

## git

<https://github.com/yoshiko2/Movie_Data_Capture>

```bash
git remote add upstream git@github.com:yoshiko2/Movie_Data_Capture.git

git fetch upstream

git merge 6.6.7
```
