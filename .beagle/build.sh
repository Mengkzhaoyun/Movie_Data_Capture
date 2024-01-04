#! /bin/sh

rm -rf ./build/Movie_Data_Capture ./dist/Movie_Data_Capture

python3 -m venv .venv

source .venv/bin/activate

pip install \
      -i https://pypi.tuna.tsinghua.edu.cn/simple \
      --upgrade \
      pip \
      pyinstaller

pip install \
      -i https://pypi.tuna.tsinghua.edu.cn/simple \
      -r requirements.txt

pip install \
      -i https://pypi.tuna.tsinghua.edu.cn/simple \
      --no-deps \
      face_recognition

pyinstaller \
        -D Movie_Data_Capture.py \
        --python-option u \
        --noconfirm \
        --hidden-import "ImageProcessing.cnn" \
        --add-data "$(python -c 'import cloudscraper as _; print(_.__path__[0])' | tail -n 1):cloudscraper" \
        --add-data "$(python -c 'import opencc as _; print(_.__path__[0])' | tail -n 1):opencc" \
        --add-data "$(python -c 'import face_recognition_models as _; print(_.__path__[0])' | tail -n 1):face_recognition_models" \
        --add-data "Img:Img" \
        --add-data "scrapinglib:scrapinglib"

cp ./config.ini ./dist/Movie_Data_Capture/config.template
