#!/bin/sh

# ============================================================
# PS5 Monitoring Service - Secure Entrypoint
# ============================================================
#
# Responsibilities:
#   - Read the Supervisor-managed configuration as root.
#   - Create a private temporary configuration directory.
#   - Copy configuration without exposing its contents.
#   - Drop privileges before starting the Python application.
#
# The Supervisor-managed options.json is never modified.
# ============================================================

set -eu

SOURCE_CONFIG="/data/options.json"
RUNTIME_DIRECTORY="/run/ps5-monitor"
RUNTIME_CONFIG="${RUNTIME_DIRECTORY}/options.json"

APP_UID="100"
APP_GID="101"

# Restrict permissions for newly created files.
umask 077

if [ ! -f "${SOURCE_CONFIG}" ]; then
    echo "ERROR: Supervisor options file not found." >&2
    exit 1
fi

# Ensure the private runtime directory exists.
mkdir -p "${RUNTIME_DIRECTORY}"

# The directory must remain inaccessible to unrelated users.
chown "${APP_UID}:${APP_GID}" "${RUNTIME_DIRECTORY}"
chmod 700 "${RUNTIME_DIRECTORY}"

# Copy configuration without printing credentials.
cp "${SOURCE_CONFIG}" "${RUNTIME_CONFIG}"

chown "${APP_UID}:${APP_GID}" "${RUNTIME_CONFIG}"
chmod 600 "${RUNTIME_CONFIG}"

# Confirm that persistent storage is writable by the app user.
if ! su-exec "${APP_UID}:${APP_GID}" \
    test -w /data; then
    echo "ERROR: Persistent data directory is not writable." >&2
    exit 1
fi

# Tell the Python configuration module where to read options.
export PS5_MONITOR_CONFIG_PATH="${RUNTIME_CONFIG}"

echo "PS5 Monitoring Service: configuration prepared."
echo "PS5 Monitoring Service: dropping privileges."

# Replace the entrypoint process with the unprivileged service.
# Signals are delivered directly to the Python application.
exec su-exec "${APP_UID}:${APP_GID}" \
    python -u /app/main.py
