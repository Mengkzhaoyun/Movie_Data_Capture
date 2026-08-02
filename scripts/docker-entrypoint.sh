#!/bin/sh

# The lock lives on the shared config volume, so it also serializes separate
# containers that were started with the same /config mount. Keep descriptor 9
# open across gosu/exec; flock will release it automatically when MDC exits.
mkdir -p /config
lock_file="/config/.mdc.lock"
exec 9>"${lock_file}"
if ! flock -n 9; then
    echo "---Movie_Data_Capture is already running for this config volume; exiting...---"
    exit 0
fi

# Setup PUID/PGID for correct volume permissions (LinuxServer.io style)
PUID=${PUID:-1000}
PGID=${PGID:-1000}

# Update mdc user UID and GID to match the host
groupmod -o -g "$PGID" mdc
usermod -o -u "$PUID" mdc

config_file="/config/config.ini"

echo "---Checking configuration...---"
# Fix volume permissions before dropping privileges
chown mdc:mdc /config /data

# Migration for legacy mdc.ini users
if [ -f "/config/mdc.ini" ] && [ ! -f "${config_file}" ]; then
    echo "---Migrating old mdc.ini to config.ini---"
    mv /config/mdc.ini "${config_file}"
    chown mdc:mdc "${config_file}"
fi

if [ ! -f "${config_file}" ]; then
    echo "---Config file missing, creating from template...---"
    # Create the file as root, then hand ownership to mdc
    cp /app/config.ini "${config_file}"
    chown mdc:mdc "${config_file}"
    echo "---Default configuration created at /config/config.ini---"
fi

echo "---Starting Movie_Data_Capture...---"
cd /data

# Drop privileges and execute as the mdc user
exec gosu mdc /app/Movie_Data_Capture
