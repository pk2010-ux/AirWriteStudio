# AirWrite Studio — Devlog

## Overview

AirWrite Studio is a hands-free digital canvas built with Python and PyQt6. It uses webcam-based hand tracking and gesture detection to let users draw, erase, select, and manipulate canvas content without a mouse or stylus.

## Current Status

- Core application structure is in place with `main.py`, UI modules, tracking modules, and canvas rendering.
- Hand gestures are detected and mapped to canvas actions through MediaPipe landmark tracking.
- Gesture control covers drawing, erasing, object selection, dragging, scaling, and neutral/stop states.
- Voice command support is planned via Vosk and the `tracking/voice_commander.py` module.
- The canvas supports export formats and workspace management via native file handling.

## Features Implemented

- Gesture-based drawing and erasing
- Shape recognition and smart geometry snapping
- Text conversion support using OCR integration pathways
- Grid templates and presentation-friendly laser/highlighter modes
- Undo/redo history architecture
- Clean dark UI layout using PyQt6 widgets and custom styling

## Project Structure

- `main.py` — Application entry point
- `config.py`, `utils.py` — configuration and helper utilities
- `canvas/` — canvas engine, widgets, object rendering, serialization, shape recognition, export
- `tracking/` — hand tracker, gesture detector, smoother, voice commander
- `ui/` — main window, sidebar, camera widget, toast notifications, styles
- `assets/` — model files, Vosk speech resources, hand landmarker task files

## Recent Work

### Cross-Platform Support — Linux & macOS (2026-07-18)

Made the entire codebase compatible with Linux and macOS. Previously it only ran on Windows due to a few hardcoded assumptions. No separate `.py` files were needed per OS — just small conditional checks at 3 critical points.

**Requirements files:**
- Renamed `requirements.txt` → `win_requirements.txt`
- Created `requirements_linux.txt` (with `apt install` notes for Tesseract, PortAudio, OpenGL libs, XCB)
- Created `requirements_macos.txt` (with `brew install` notes for Tesseract, PortAudio)
- Created a new universal `requirements.txt` that works on all platforms
- Found and added two missing packages to all files: `PyQt6-Svg` (needed by `svg_exporter.py`) and `Pillow` (needed by `pytesseract`)

**Code fixes:**

| File | What was wrong | What was done |
|------|----------------|---------------|
| `config.py` | No platform-aware font constants existed | Added `SYSTEM_UI_FONT` and `SYSTEM_EMOJI_FONT` that resolve per-OS (Segoe UI on Windows, .AppleSystemUIFont on macOS, sans-serif on Linux) |
| `app_logging.py` | Used `LOCALAPPDATA` env var, which only exists on Windows | Replaced with `_get_app_data_dir()` that picks the right path: `%LOCALAPPDATA%` on Windows, `~/Library/Application Support/` on macOS, `$XDG_DATA_HOME` or `~/.local/share/` on Linux |
| `tracking/hand_tracker.py` | Used `cv2.CAP_DSHOW` (DirectShow, Windows-only camera backend) | Made conditional — only uses DirectShow on Windows, uses default backend on Linux (V4L2) and macOS (AVFoundation) |
| `canvas/text_object.py` | Hardcoded `"Segoe UI"` font family | Now uses `SYSTEM_UI_FONT` from config |
| `ui/camera_widget.py` | Hardcoded `"Segoe UI Emoji"` and `"Segoe UI"` | Now uses `SYSTEM_EMOJI_FONT` and `SYSTEM_UI_FONT` from config |
| `canvas/grid_renderer.py` | Hardcoded `"Segoe UI"` in Cornell notes template | Now uses `SYSTEM_UI_FONT` from config |
| `ui/toast_widget.py` | Hardcoded `"Segoe UI"` for icon rendering | Now uses `SYSTEM_UI_FONT` from config |

**Build script:**
- Created `build.sh` — bash equivalent of `build.ps1` for Linux/macOS PyInstaller builds (uses `:` as the `--add-data` separator instead of `;`)

**What didn't need changing:**
- `ui/styles.py` already had cross-platform font-family fallbacks (`-apple-system`, `sans-serif`)
- `canvas/ocr_engine.py` already had platform-specific Tesseract path detection
- All core dependencies (PyQt6, OpenCV, MediaPipe, NumPy, SciPy) are inherently cross-platform
- `README.md` was not touched

**Verification:**
- All 21 Python modules import successfully after the changes

### Earlier work

- Built the main interactive canvas and stabilized gesture interactions.
- Added smart UI for tool selection and camera control.
- Integrated offline voice command support architecture with Vosk assets.
- Added documentation in `README.md` to describe features, installation, and usage.
- Created a web-based demo version using Flask and Hugging Face Spaces Docker deployment. Note: The web demo relies on server-side processing for MediaPipe gestures and may experience latency or glitchiness depending on the user's hardware limitations, webcam quality, and network speed.

## Challenges

- Ensuring reliable hand detection across different lighting conditions and webcams.
- Mapping natural gestures into consistent canvas commands without accidental triggers.
- Keeping performance smooth for real-time drawing and gesture recognition.
- Handling network latency and server-side model processing for the web demo without native client-side binaries.
- Making font and path choices work across Windows, macOS, and Linux without scattering platform checks everywhere (solved by centralizing in `config.py`).

## Next Milestones

1. Finalize gesture calibration and user feedback flow.
2. Complete OCR text conversion and editable text object workflow.
3. ~~Add full export support for PNG, PDF, SVG, and native `.air` saves.~~ Done.
4. Polish the UI, including toolbar behavior, status indicators, and onboarding hints.
5. Add tests for canvas serialization and gesture classification.
6. ~~Make the app cross-platform (Linux, macOS).~~ Done.
7. Add a `requirements-dev.txt` for development tooling, formatting, and testing.

## Notes for Future Development

- Consider adding a `CHANGELOG.md` or release notes for future version tracking.
- Keep `venv/` and `__pycache__/` ignored in source control, and preserve only source files and assets.
- Linux users may need `sudo apt install libegl1 libgl1-mesa-glx libxcb-xinerama0 libxcb-cursor0` for PyQt6 to work properly.
- macOS users should install Tesseract and PortAudio via Homebrew if they want OCR and voice commands.

---

_Last updated: 2026-07-18_
