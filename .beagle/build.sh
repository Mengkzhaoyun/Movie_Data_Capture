#! /bin/sh

apt-get -y update && apt-get -y upgrade \
    && apt install -y -q \
        bash \
        wget \
        binutils \
        liblapack-dev \
        libatlas-base-dev \
    && apt-get autoremove --purge -y \
    && apt-get clean -y

python3 -m venv /opt/venv && . /opt/venv/bin/activate \
    && pip install \
        -i https://pypi.tuna.tsinghua.edu.cn/simple \
        --upgrade \
        pip \
        pyinstaller \
    && if [ -n "$(ls -A ./dist)" ]; then pip install ./dist/*.whl; fi \
    && pip install -r requirements.txt  \
    && pip install face_recognition -i https://pypi.tuna.tsinghua.edu.cn/simple --no-deps \
    && pyinstaller \
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
