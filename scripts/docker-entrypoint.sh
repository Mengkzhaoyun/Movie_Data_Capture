#! /bin/sh

config_file="/config/mdc.ini"

echo "---Checking configuration...---"
if [ ! -d /config ]; then
    mkdir -p /config
fi

if [ ! -f "${config_file}" ]; then
    echo "---Config file missing, creating from template...---"
    cp /app/config.template "${config_file}"
    echo "请修改 /config/mdc.ini 后重启容器！"
    exit 1
fi

echo "---Starting Movie_Data_Capture...---"
cd /data
exec /app/Movie_Data_Capture