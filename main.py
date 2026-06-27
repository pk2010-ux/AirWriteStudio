"""
AirWrite Studio - Entry Point
================================
Camera-based hands-free writing application.

Launch the app:
    python main.py

Requirements:
    pip install -r requirements.txt

Controls:
    - Start camera from sidebar, then use hand gestures:
      - Thumb + Index pinch = Draw
      - Closed fist + thumb out = Erase
      - Single Index finger point = Select
      - Three fingers together = Drag selected objects
      - Pinky + Thumb pinch = Zoom/Pan
      - Open palm = Neutral

    - Sidebar tools:
      - Laser pointer (fading strokes)
      - Highlighter (semi-transparent)
      - Pressure width (speed-based)
      - Smart shapes (auto-detect geometry)
      - Convert to text (OCR)
      - Grid templates (lines, graph, dots, music, Cornell)
      - Voice commands (offline)
      - Gesture calibration

Keyboard Shortcuts:
    Ctrl+Z     Undo
    Ctrl+Y     Redo
    Ctrl+S     Save as PNG
    Ctrl+E     Export as PDF
    Ctrl+N     Clear canvas
    F11        Toggle fullscreen
"""

import os
import sys
import logging

# Suppress noisy MediaPipe telemetry and TensorFlow Lite warnings
os.environ["GLOG_minloglevel"] = "2"          # Suppress INFO/WARNING from glog
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"      # Suppress TF Lite logs
os.environ["GRPC_VERBOSITY"] = "ERROR"         # Suppress gRPC noise
os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"      # Force CPU (avoids GPU init warnings)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QSurfaceFormat
from app_logging import setup_logging
from ui.main_window import MainWindow
from ui.styles import Styles


def main():
    """Initialize and run the AirWrite Studio application."""
    log_file = setup_logging()
    logging.info("Log file: %s", log_file)

    # Enable 4x MSAA for QOpenGLWidget to fix pixelated strokes
    fmt = QSurfaceFormat()
    fmt.setSamples(4)
    QSurfaceFormat.setDefaultFormat(fmt)

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("AirWrite Studio")
    app.setOrganizationName("AirWrite")

    # Apply global dark theme stylesheet
    app.setStyleSheet(Styles.get_main_stylesheet())

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
