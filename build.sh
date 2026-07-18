#!/usr/bin/env bash
# Build script for AirWrite Studio (Linux / macOS)
# Requires pyinstaller installed in the active Python environment.
#
# Usage:
#   chmod +x build.sh
#   ./build.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
EXE_NAME="AirWriteStudio"

echo "Building ${EXE_NAME}..."

# Determine the --add-data separator (: on Unix, ; on Windows/MSYS)
SEP=":"

python3 -m PyInstaller \
    --noconfirm \
    --clean \
    --windowed \
    --onefile \
    --name "${EXE_NAME}" \
    --add-data "assets${SEP}assets" \
    --collect-data mediapipe \
    --collect-binaries mediapipe \
    --collect-data vosk \
    --collect-binaries vosk \
    --hidden-import mediapipe.tasks.python \
    --hidden-import mediapipe.tasks.python.vision \
    --hidden-import mediapipe.tasks.python.vision.hand_landmarker \
    --hidden-import mediapipe.tasks.python.vision.core.vision_task_running_mode \
    "${PROJECT_ROOT}/main.py"

echo "Build finished. Check the dist/ folder."

# Log file location varies by platform
if [[ "$(uname)" == "Darwin" ]]; then
    echo "If camera startup fails, check: ~/Library/Application Support/AirWrite Studio/airwrite.log"
else
    LOG_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/AirWrite Studio"
    echo "If camera startup fails, check: ${LOG_DIR}/airwrite.log"
fi
