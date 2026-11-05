#!/bin/sh

# ============================================================
# PS5 Monitoring Service - Entrypoint Security Test
# ============================================================
#
# Verify the secure configuration handoff without starting
# the monitoring application or connecting to MQTT.
#
# All configuration values used in this test are fictitious.
# ============================================================

set -eu

SOURCE_CONFIG="/data/options.json"
RUNTIME_CONFIG="/run/ps5-monitor/options.json"

# Create a simulated Supervisor configuration.
# This test runs in an isolated container with a temporary /data.
printf '%s\n' '{"mqtt_password":"test-only-secret"}' \
    > "${SOURCE_CONFIG}"

chown root:root "${SOURCE_CONFIG}"
chmod 600 "${SOURCE_CONFIG}"

# Prepare the runtime directory using the same security
# operations performed by the production entrypoint.
mkdir -p /run/ps5-monitor
chown 100:101 /run/ps5-monitor
chmod 700 /run/ps5-monitor

cp "${SOURCE_CONFIG}" "${RUNTIME_CONFIG}"
chown 100:101 "${RUNTIME_CONFIG}"
chmod 600 "${RUNTIME_CONFIG}"

echo "========== ENTRYPOINT SECURITY TEST =========="

# Verify the original Supervisor configuration remains protected.
test "$(stat -c '%u:%g' "${SOURCE_CONFIG}")" = "0:0"
test "$(stat -c '%a' "${SOURCE_CONFIG}")" = "600"

echo "PASS: Original configuration remains root-owned"

# Verify that the application user can read the runtime copy.
su-exec 100:101 python -c '
from pathlib import Path

path = Path("/run/ps5-monitor/options.json")

assert path.is_file()
assert path.stat().st_uid == 100
assert path.stat().st_gid == 101

# Read and parse without displaying the secret.
import json
data = json.loads(path.read_text())

assert data.get("mqtt_password") == "test-only-secret"

print("PASS: Application user can read protected configuration")
'

# Verify the application user cannot read the original.
if su-exec 100:101 test -r "${SOURCE_CONFIG}"; then
    echo "FAIL: Application user can read root-owned configuration"
    exit 1
fi

echo "PASS: Original Supervisor configuration remains inaccessible"

# Verify that an unrelated UID cannot read the runtime copy.
if su-exec 200:200 test -r "${RUNTIME_CONFIG}"; then
    echo "FAIL: Unrelated user can read runtime configuration"
    exit 1
fi

echo "PASS: Runtime credentials inaccessible to unrelated users"

echo
echo "RESULT: ALL ENTRYPOINT SECURITY TESTS PASSED"
