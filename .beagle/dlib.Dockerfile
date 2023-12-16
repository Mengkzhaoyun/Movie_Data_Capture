ARG DLIB_DIR=/tmp/dlib
ARG DLIB_WHL_DIR=${DLIB_DIR}/dist

ARG BASE
FROM $BASE

# https://github.com/ageitgey/face_recognition/blob/master/Dockerfile
RUN apt-get -y update
RUN apt-get install -y --fix-missing \
    build-essential \
    cmake \
    gfortran \
    git \
    wget \
    curl \
    graphicsmagick \
    libgraphicsmagick1-dev \
    libatlas-base-dev \
    libgtk2.0-dev \
    libjpeg-dev \
    liblapack-dev \
    pkg-config \
    python3-dev \
    python3-numpy \
    software-properties-common \
    zip \
    libavdevice-dev \
    libavfilter-dev \
    libavformat-dev \
    libavcodec-dev \
    libswresample-dev \
    libswscale-dev \
    libavutil-dev \
    libopenblas-dev \
    libblas-dev \
    && apt-get clean && rm -rf /tmp/* /var/tmp/*

ARG DLIB_VERSION=v19.24.2
ARG DLIB_DIR

# dlib-bin repotory dlib-wheels steps: https://github.com/alesanfra/dlib-wheels/blob/master/.github/workflows/build.yaml
RUN mkdir -p ${DLIB_DIR} && \
    git config --global http.https://github.com.proxy socks5://www.ali.wodcloud.com:1283 && \
    git clone -b "${DLIB_VERSION}" --single-branch https://github.com/davisking/dlib.git ${DLIB_DIR} && \
    cd ${DLIB_DIR} && \
    # change dlib python module desc
    sed -i'' -e "s/name='dlib'/name='dlib-bin'/" setup.py && \
    sed -i'' -e "s/version=read_version_from_cmakelists('dlib\/CMakeLists.txt')/version='$DLIB_VERSION'/" setup.py && \
    sed -i'' -e "s/url='https:\/\/github\.com\/davisking\/dlib'/url='https:\/\/github\.com\/navyd\/docker-mdc'/" setup.py && \
    sed -i'' -e "s/_cmake_extra_options = \[\]/_cmake_extra_options = \['-DDLIB_NO_GUI_SUPPORT=ON'\]/" setup.py && \
    # build dlib: https://github.com/davisking/dlib#compiling-dlib-python-api
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple build && \
    python -m build --wheel && \
    # check
    pip install ./dist/*.whl
