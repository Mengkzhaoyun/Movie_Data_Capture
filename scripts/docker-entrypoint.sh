#!/bin/sh

# Setup PUID/PGID for correct volume permissions (LinuxServer.io style)
PUID=${PUID:-1000}
PGID=${PGID:-1000}

# Update mdc user UID and GID to match the host
groupmod -o -g "$PGID" mdc
usermod -o -u "$PUID" mdc

config_file="/config/mdc.ini"

echo "---Checking configuration...---"
if [ ! -d /config ]; then
    mkdir -p /config
fi

# Fix volume permissions before dropping privileges
chown mdc:mdc /config /data

if [ ! -f "${config_file}" ]; then
    echo "---Config file missing, creating from template...---"
    # Create the file as root, then hand ownership to mdc
    cp /app/config.template "${config_file}"
    chown mdc:mdc "${config_file}"
    echo "请修改 /config/mdc.ini 后重启容器！"
    exit 1
fi

echo "---Starting Movie_Data_Capture...---"
cd /data

# Drop privileges and execute as the mdc user
exec gosu mdc /app/Movie_Data_Capture