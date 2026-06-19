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

## Next Milestones

1. Finalize gesture calibration and user feedback flow.
2. Complete OCR text conversion and editable text object workflow.
3. Add full export support for PNG, PDF, SVG, and native `.air` saves.
4. Polish the UI, including toolbar behavior, status indicators, and onboarding hints.
5. Add tests for canvas serialization and gesture classification.

## Notes for Future Development

- Add a `requirements-dev.txt` for development tooling, formatting, and testing.
- Consider adding a `CHANGELOG.md` or release notes for future version tracking.
- Keep `venv/` and `__pycache__/` ignored in source control, and preserve only source files and assets.

---

_Last updated: 2026-06-19_
