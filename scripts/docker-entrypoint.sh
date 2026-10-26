#!/bin/sh

# Acquire non-blocking exclusive locks across all possible shared mounts BEFORE
# printing any startup banners:
# - /tmp/.mdc.entrypoint.lock (same container)
# - /config/.mdc.lock (shared /config volume)
# - /data (shared /data volume)
# - /config/config.ini (single-file bind mount of config.ini)
# - source_folder from config.ini (custom host media mount, e.g. /share/...)
mkdir -p /config /data /tmp
config_file="/config/config.ini"

exec 9>"/config/.mdc.lock"
exec 7>"/tmp/.mdc.entrypoint.lock"
exec 6<"/data"
if ! flock -n 9 || ! flock -n 7 || ! flock -n 6; then
    echo "---Movie_Data_Capture is already running; exiting...---"
    exit 0
fi

# Migration for legacy mdc.ini users before locking config_file
if [ -f "/config/mdc.ini" ] && [ ! -f "${config_file}" ]; then
    echo "---Migrating old mdc.ini to config.ini---"
    mv /config/mdc.ini "${config_file}"
fi

if [ -f "${config_file}" ]; then
    exec 8<"${config_file}"
    if ! flock -n 8; then
        echo "---Movie_Data_Capture is already running for ${config_file}; exiting...---"
        exit 0
    fi
    source_dir=$(sed -n 's/^[[:space:]]*source_folder[[:space:]]*=[[:space:]]*\([^;#]*\).*/\1/p' "${config_file}" | head -n 1 | sed 's/[[:space:]]*$//' | tr -d '\r')
    if [ -n "${source_dir}" ] && [ "${source_dir}" != "./" ] && [ "${source_dir}" != "." ] && [ -d "${source_dir}" ]; then
        exec 5<"${source_dir}"
        if ! flock -n 5; then
            echo "---Movie_Data_Capture is already running for source_folder '${source_dir}'; exiting...---"
            exit 0
        fi
    fi
fi

# Setup PUID/PGID for correct volume permissions (LinuxServer.io style)
PUID=${PUID:-1000}
PGID=${PGID:-1000}

# Update mdc user UID and GID to match the host
groupmod -o -g "$PGID" mdc
usermod -o -u "$PUID" mdc

echo "---Checking configuration...---"
# Fix volume permissions before dropping privileges
chown mdc:mdc /config /data

if [ ! -f "${config_file}" ]; then
    echo "---Config file missing, creating from template...---"
    # Create the file as root, then hand ownership to mdc
    cp /app/config.ini "${config_file}"
    chown mdc:mdc "${config_file}"
    echo "---Default configuration created at /config/config.ini---"
    exec 8<"${config_file}"
    flock -n 8 || exit 0
else
    chown mdc:mdc "${config_file}" 2>/dev/null || true
fi

echo "---Starting Movie_Data_Capture...---"
cd /data

export MDC_ENTRYPOINT_LOCKED=1
# Drop privileges and execute as the mdc user
exec gosu mdc /app/Movie_Data_Capture
