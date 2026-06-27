# Build script for AirWrite Studio
# Requires pyinstaller installed in the active Python environment.

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$assetData = "assets;assets"
$exeName = "AirWriteStudio"

Write-Host "Building $exeName..."

$args = @(
    "-3", "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--windowed",
    "--onefile",
    "--name", $exeName,
    "--add-data", $assetData,
    "--collect-data", "mediapipe",
    "--collect-binaries", "mediapipe",
    "--collect-data", "vosk",
    "--collect-binaries", "vosk",
    "--hidden-import", "mediapipe.tasks.python",
    "--hidden-import", "mediapipe.tasks.python.vision",
    "--hidden-import", "mediapipe.tasks.python.vision.hand_landmarker",
    "--hidden-import", "mediapipe.tasks.python.vision.core.vision_task_running_mode",
    "$projectRoot\main.py"
)

py @args
Write-Host "Build finished. Check the dist folder."
Write-Host "If camera startup fails, check: $env:LOCALAPPDATA\AirWrite Studio\airwrite.log"
