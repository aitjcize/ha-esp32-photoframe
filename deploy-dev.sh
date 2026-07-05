#!/bin/bash
# deploy-dev.sh - Deploy the custom integration to Home Assistant for testing.
#
# Copies custom_components/esp32_photoframe onto the HA host with scp and
# restarts Home Assistant Core so the new code is picked up.
#
# Requirements on the HA host:
#   - The SSH add-on (port 22) with your key authorized, exposing /config and
#     the `ha` CLI.
#
# Usage: ./deploy-dev.sh [homeassistant-host]   (default: root@homeassistant.local)
set -euo pipefail

HA_HOST="${1:-root@homeassistant.local}"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPONENT="esp32_photoframe"
CONFIG_DIR="${HA_CONFIG_DIR:-/config}"
REMOTE_DIR="${CONFIG_DIR}/custom_components/${COMPONENT}"

echo "=== Staging ${COMPONENT} (stripping __pycache__) ==="
STAGE="$(mktemp -d)"
trap 'rm -rf "${STAGE}"' EXIT
cp -R "${LOCAL_DIR}/custom_components/${COMPONENT}" "${STAGE}/${COMPONENT}"
find "${STAGE}/${COMPONENT}" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find "${STAGE}/${COMPONENT}" -type f -name '*.pyc' -delete 2>/dev/null || true

echo "=== Copying to ${HA_HOST}:${REMOTE_DIR} ==="
ssh "${HA_HOST}" "rm -rf '${REMOTE_DIR}' && mkdir -p '${CONFIG_DIR}/custom_components'"
scp -O -r "${STAGE}/${COMPONENT}" "${HA_HOST}:${CONFIG_DIR}/custom_components/"

echo "=== Restarting Home Assistant Core ==="
ssh "${HA_HOST}" "ha core restart"

echo "=== Done. Watch logs with: ssh ${HA_HOST} 'ha core logs -f' ==="
