# Build script for AirWrite Studio
# Requires pyinstaller installed in the active Python environment.

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$assetData = "assets;assets"
$voskData = "venv\Lib\site-packages\vosk;vosk"
$exeName = "AirWriteStudio"

Write-Host "Building $exeName..."
py -3 -m PyInstaller --windowed --onefile --name $exeName --add-data $assetData --add-data $voskData "$projectRoot\main.py"
Write-Host "Build finished. Check the dist folder."