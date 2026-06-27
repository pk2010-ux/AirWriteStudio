# AirWrite Studio

<div align="center">
  <h3>A hands-free digital canvas that lets you draw, erase, and annotate using nothing but your hand gestures in front of a webcam.</h3>
</div>

<br />

**AirWrite Studio** is a real-time, camera-based drawing application. It uses MediaPipe hand tracking to detect your hand through a standard webcam and translates natural hand gestures into canvas actions — no stylus, no touchscreen, no mouse required.

## 🚀 Features

*   **Gesture-Based Control:**
    *   **Pinch thumb + index finger:** Draw on the canvas.
    *   **Closed fist with thumb out:** Erase strokes.
    *   **Point with index finger:** Lasso-select objects.
    *   **Three fingers together:** Drag selected objects.
    *   **Thumb + middle pinch:** Scale up.
    *   **Thumb + ring pinch:** Scale down.
    *   **Open palm:** Neutral / stop.
*   **Drawing Tools:**
    *   Pen with a 12-color palette and adjustable size.
    *   Laser pointer mode with fading strokes (ideal for presentations).
    *   Highlighter with semi-transparent overlays.
    *   Pressure-sensitive width that responds to hand speed.
    *   Galaxy brush for decorative particle strokes.
*   **Smart Canvas Features:**
    *   **Smart Shape Recognition:** Automatically snaps freehand circles, rectangles, triangles, and lines into clean geometry.
    *   **OCR Text Conversion:** Select handwritten strokes and convert them to editable text via Tesseract.
    *   **Grid Templates:** Lined, graph, dot grid, music staff, and Cornell notes.
*   **Advanced Capabilities:**
    *   **Offline Voice Commands:** Say "undo", "clear", "color red", etc. via Vosk speech recognition.
    *   **Gesture Calibration Wizard:** Tune detection thresholds to your hand size.
    *   **History:** Full undo/redo history (up to 50 steps).
    *   **Export:** Export your canvas to PNG, PDF, and SVG.
    *   **Workspace Management:** Save and load your work in a native `.air` format.
*   **Premium UI:** Minimal dark UI inspired by Linear, Apple, and Notion — clean typography (Inter), restrained color palette, consistent 8px spacing grid, and subtle hover states.

## 🛠️ Technology Stack

*   **Python 3**
*   **PyQt6:** Hardware-accelerated canvas (OpenGL with 4x MSAA) and user interface.
*   **MediaPipe:** Real-time, robust hand landmark detection.
*   **One Euro Filter:** Advanced pointer smoothing and jitter reduction.
*   **qtawesome:** Professional vector icons (FontAwesome / Material Design).
*   **NumPy & OpenCV:** Shape recognition algorithms and image processing.
*   **Tesseract:** OCR capabilities (optional dependency).
*   **Vosk:** Offline speech recognition (optional dependency).

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/pk2010-ux/AirWriteStudio.git
    cd AirWriteStudio
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    
    # On Windows:
    venv\Scripts\activate
    
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Optional Dependencies (for full feature set):**
    *   **OCR (Convert to Text):** Install [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) on your system.
    *   **Voice Commands:** Install Vosk:
        ```bash
        pip install vosk pyaudio
        ```
        *(Note: You may also need to download a Vosk model and place it in the appropriate directory as prompted by the app).*

## 📦 Packaging

To build a Windows executable using PyInstaller:

```powershell
pip install pyinstaller
.\build.ps1
```

This creates a bundled app in `dist\AirWriteStudio.exe`.

## 🎮 Usage

Launch the application:

```bash
python main.py
```

1.  Click **Start Camera** in the sidebar.
2.  Hold your hand up to the camera.
3.  Use the gestures listed above (e.g., pinch to draw) to interact with the canvas.
4.  Use the sidebar to change tools, colors, toggle smart shapes, or export your work.

### Keyboard Shortcuts
*   `Ctrl+Z`: Undo
*   `Ctrl+Y`: Redo
*   `Ctrl+S`: Save as PNG
*   `Ctrl+E`: Export as PDF
*   `Ctrl+N`: Clear canvas
*   `F11`: Toggle fullscreen
*   `Home`: Reset zoom/pan view

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
Feel free to check [issues page](https://github.com/pk2010-ux/AirWriteStudio/issues).

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.
