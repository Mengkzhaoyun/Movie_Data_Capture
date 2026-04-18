ARG BASE=debian:bookworm-slim

FROM $BASE

ARG TARGETARCH

LABEL maintainer="VergilGao"
LABEL build_from="https://github.com/yoshiko2/Movie_Data_Capture"
LABEL org.opencontainers.image.source="https://github.com/VergilGao/docker-mdc"

ENV TZ="Asia/Shanghai"
ENV UID=1000
ENV GID=1000
ENV UMASK=002

RUN \
    apt-get -y update && apt-get -y upgrade \
    && apt install -y -q \
        chromium \
    && apt-get autoremove --purge -y \
    && apt-get clean -y \
    && mkdir -p /data /config /app \
    && groupadd -g ${GID} mdc \
    && useradd -u ${UID} -g mdc -d /config -s /bin/sh mdc \
    && chown -R mdc:mdc /data /config /app

ADD --chmod=755 scripts/docker-entrypoint.sh /docker-entrypoint.sh

# Install the exact pre-compiled binary based on architecture passed by host builder
COPY dist/Movie_Data_Capture/ /app/
# Explicitly copy the clean default configuration template
COPY config.ini /app/config.template

VOLUME [ "/data", "/config" ]

USER mdc

ENTRYPOINT ["/docker-entrypoint.sh"]
