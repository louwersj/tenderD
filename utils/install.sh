#!/bin/bash

# Root check
if [[ "$EUID" -ne 0 ]]; then
  echo "[tenderD] Error: This script must be run as root" >&2
  exit 1
fi

BASE_DIR="/opt/tenderD"
CONF_DIR="$BASE_DIR/conf"
BIN_DIR="$BASE_DIR/bin"
SCRIPT_DIR="$BASE_DIR/script"
UTILS_DIR="$BASE_DIR/utils"
LOG_DIR="$BASE_DIR/logs"
DOWNLOAD_DIR="$BASE_DIR/downloads"
WATCH_DIR="$BASE_DIR/watch"

echo "[tenderD] Creating directory structure under $BASE_DIR"
mkdir -p "$CONF_DIR" "$BIN_DIR" "$SCRIPT_DIR" "$UTILS_DIR" "$LOG_DIR" "$DOWNLOAD_DIR" "$WATCH_DIR"

echo "[tenderD] Downloading config.json..."
curl -fsSL "https://raw.githubusercontent.com/louwersj/tenderD/refs/heads/main/conf/config.json" -o "$CONF_DIR/config.json"

echo "[tenderD] Downloading startTenderD..."
curl -fsSL "https://raw.githubusercontent.com/louwersj/tenderD/refs/heads/main/bin/startTenderD" -o "$BIN_DIR/startTenderD"
chmod +x "$BIN_DIR/startTenderD"

echo "[tenderD] Downloading tenderDscheduler.py..."
curl -fsSL "https://raw.githubusercontent.com/louwersj/tenderD/refs/heads/main/scripts/tenderDscheduler.py" -o "$SCRIPT_DIR/tenderDscheduler.py"

echo "[tenderD] Downloading prepareNode.sh..."
curl -fsSL "https://raw.githubusercontent.com/louwersj/tenderD/refs/heads/main/utils/prepareNode.sh" -o "$UTILS_DIR/prepareNode.sh"
chmod +x "$UTILS_DIR/prepareNode.sh"

echo "[tenderD] Running prepareNode.sh..."
"$UTILS_DIR/prepareNode.sh"

echo "[tenderD] Installation complete!"
