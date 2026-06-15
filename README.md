# AirWrite Studio ✨

<div align="center">

### Draw in the air. Control with gestures. No mouse required.

A futuristic hand-tracking whiteboard powered by computer vision, gesture recognition, and real-time rendering.

<br>

![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge\&logo=python)
![PyQt6](https://img.shields.io/badge/UI-PyQt6-black?style=for-the-badge)
![MediaPipe](https://img.shields.io/badge/Tracking-MediaPipe-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-red?style=for-the-badge)

</div>

---

# ✨ Overview

**AirWrite Studio** transforms your webcam into a fully interactive digital canvas.

Using real-time hand tracking with **MediaPipe**, the app detects natural gestures and converts them into drawing actions, object manipulation, voice-controlled commands, and smart canvas interactions.

No stylus.
No touchscreen.
Just your hands and a camera. Humanity really looked at mice and keyboards and decided *finger wizardry* was the next logical step.

---

# 🎮 Gesture Controls

| Gesture                   | Action                |
| ------------------------- | --------------------- |
| 🤏 Thumb + Index Pinch    | Draw                  |
| ✊ Closed Fist + Thumb Out | Erase                 |
| ☝️ Index Finger Point     | Lasso Select          |
| 🤌 Three Fingers Together | Move Selected Objects |
| 👌 Thumb + Middle Pinch   | Scale Up              |
| 🤞 Thumb + Ring Pinch     | Scale Down            |
| ✋ Open Palm               | Neutral / Pause       |

---

# 🚀 Features

## 🎨 Smart Drawing System

* Smooth real-time drawing
* Adjustable brush size
* 12-color palette
* Pressure-sensitive strokes
* Highlighter mode
* Laser pointer mode
* Galaxy particle brush
* Advanced stroke smoothing using **One Euro Filter**

---

## 🧠 AI-Powered Canvas Features

### Smart Shape Recognition

Draw rough shapes and let AirWrite automatically clean them into:

* Circles
* Rectangles
* Triangles
* Straight lines

### OCR Text Conversion

Convert handwritten strokes into editable text using **Tesseract OCR**.

### Voice Commands

Offline speech recognition powered by **Vosk**:

* `"undo"`
* `"clear"`
* `"color red"`
* `"export"`
* and more...

Because apparently waving at computers wasn’t enough. Now we also yell at them.

---

## 📐 Productivity Tools

* Undo / Redo History
* Workspace Save System (`.air`)
* PNG Export
* PDF Export
* SVG Export
* Fullscreen Presentation Mode
* Zoom & Pan Controls

---

## 📄 Grid Templates

Choose from multiple canvas layouts:

* Graph Paper
* Dot Grid
* Lined Notes
* Cornell Notes
* Music Staff Paper

---

# 🖥️ UI & Experience

AirWrite Studio features a modern desktop interface inspired by:

* Linear
* Notion
* Apple Design Language

### Design Highlights

* Minimal dark theme
* Inter typography
* Subtle animations
* Clean spacing system
* Smooth hover interactions
* Hardware-accelerated OpenGL rendering

Unlike most “futuristic” open-source apps that look like abandoned router firmware from 2009.

---

# 🛠️ Tech Stack

| Technology      | Purpose                |
| --------------- | ---------------------- |
| Python 3        | Core Application       |
| PyQt6           | User Interface         |
| MediaPipe       | Hand Tracking          |
| OpenCV          | Image Processing       |
| NumPy           | Computation            |
| One Euro Filter | Motion Smoothing       |
| Tesseract OCR   | Text Recognition       |
| Vosk            | Offline Voice Commands |
| qtawesome       | Icon System            |

---

# 📦 Installation

## 1️⃣ Clone Repository

```bash
git clone https://github.com/yourusername/AirWriteStudio.git
cd AirWriteStudio
```

---

## 2️⃣ Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4️⃣ Optional Features

### OCR Support

Install **Tesseract OCR**:

https://github.com/tesseract-ocr/tesseract

### Voice Commands

```bash
pip install vosk pyaudio
```

You may also need to download a Vosk language model depending on your setup. Because software dependency chains are humanity’s preferred form of psychological warfare.

---

# ▶️ Running the App

```bash
python main.py
```

---

# ⌨️ Keyboard Shortcuts

| Shortcut   | Action         |
| ---------- | -------------- |
| `Ctrl + Z` | Undo           |
| `Ctrl + Y` | Redo           |
| `Ctrl + S` | Save PNG       |
| `Ctrl + E` | Export PDF     |
| `Ctrl + N` | Clear Canvas   |
| `F11`      | Fullscreen     |
| `Home`     | Reset Zoom/Pan |

---

# 📸 Recommended Additions

To make the repository look significantly more professional:

* Add screenshots/GIF demos
* Add an architecture diagram
* Add feature preview videos
* Add benchmark/performance stats
* Add roadmap section
* Add contribution guidelines
* Add a demo release build

A README without visuals is basically a restaurant menu with no food photos. Technically sufficient. Spiritually suspicious.

---

# 🤝 Contributing

Contributions, pull requests, feature ideas, and issue reports are welcome.

If you build something cool on top of AirWrite Studio, fork it, improve it, and unleash more gesture-controlled chaos into the world.

---

# 📜 License

Licensed under the **MIT License**.

See the `LICENSE` file for more information.
