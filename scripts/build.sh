#! /bin/sh

rm -rf ./build/Movie_Data_Capture ./dist/Movie_Data_Capture

TARGET_ARCH="${TARGET_ARCH:-amd64}"
LOCAL_ARCH=$(uname -m)
if [ "$LOCAL_ARCH" = "x86_64" ]; then
  TARGET_ARCH="amd64"
elif [ "$(echo $LOCAL_ARCH | head -c 5)" = "armv8" ]; then
  TARGET_ARCH="arm64"
elif [ "$LOCAL_ARCH" = "aarch64" ]; then
  TARGET_ARCH="arm64"
else
  echo "This system's architecture $(LOCAL_ARCH) isn't supported"
  TARGET_ARCH="unsupported"
fi

python3 -m venv .python/$TARGET_ARCH

source .python/$TARGET_ARCH/bin/activate

pip install \
  -i https://pypi.tuna.tsinghua.edu.cn/simple \
  --upgrade \
  pip \
  pyinstaller

if [ -n "$(ls -A ./dist)" ]; then
  pip install ./dist/dlib_bin-*-linux_$LOCAL_ARCH.whl
fi

pip install \
  -i https://pypi.tuna.tsinghua.edu.cn/simple \
  -r requirements.txt

pip install \
  -i https://pypi.tuna.tsinghua.edu.cn/simple \
  --no-deps \
  face_recognition

pyinstaller \
  -D src/main.py \
  -n Movie_Data_Capture \
  --python-option u \
  --noconfirm \
  --hidden-import "image_processing.cnn" \
  --hidden-import "adc_function" \
  --hidden-import "core" \
  --add-data "$(python -c 'import cloudscraper as _; print(_.__path__[0])' | tail -n 1):cloudscraper" \
  --add-data "$(python -c 'import opencc as _; print(_.__path__[0])' | tail -n 1):opencc" \
  --add-data "$(python -c 'import face_recognition_models as _; print(_.__path__[0])' | tail -n 1):face_recognition_models" \
  --add-data "src/img:img" \
  --add-data "scrapinglib:scrapinglib"
