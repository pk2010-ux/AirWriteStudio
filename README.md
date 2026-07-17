# AirWrite Studio
 
A hands-free digital canvas that lets you draw, erase, and annotate using nothing but your hand in front of a webcam, no mouse, no stylus, no touching anything
 
![Image](/image.png)

 
**AirWrite Studio** is a real-time, camera-based drawing app. Point a normal webcam at your hand, pinch your fingers together, and start drawing in mid-air like some kind of wizard who also happens to know Python. It uses MediaPipe to track your hand and turns specific finger positions into canvas actions. The first time it actually worked for me I got way too excited and startled my own cat off the desk.
 
## Try it
 
There's a browser demo running on Hugging Face Spaces if you just want to poke it without installing anything: [Try it here](https://huggingface.co/spaces/Priyajit0202/AWS-demo)
 
Heads up though, the web version runs the hand-tracking on the server instead of on your machine, so depending on your connection and how busy the server is, it can lag or get a little glitchy. If it feels laggy that isnt your webcam being bad, its just the nature of doing MediaPipe over a network instead of locally. The desktop version below doesnt have that problem since everything runs on your own machine.
 
There's also a packaged Windows executable if you dont want to touch Python at all, see the "second method" section further down.
 
## Quick start
 
If you just want to see it work: use the demo link above, give it camera access, and pinch your thumb and index finger together over the canvas.
 
If you want the real, non-laggy experience, it is a few terminal commands away, see below.
 
## Features
 
**Gesture controls** (all detected off your bare hand, no gloves or markers needed)
- Pinch thumb + index finger together, keep the other two fingers open: draws
- Close your fist but keep your thumb sticking out: erases
- Point with just your index finger, everything else curled: selects objects (I call it lasso-select in my head even though its really more of a poke-select)
- Pinch thumb, index, and middle finger together all at once: drags whatever you have selected
- Pinch thumb + middle finger: zooms in
- Pinch thumb + ring finger: zooms out
- Open palm, fingers spread: does nothing on purpose, this is your safe "stop listening to me" pose
Fair warning, it takes a minute to get your muscle memory right. I definitely erased a whole diagram by accident more than once while learning my own gestures.
 
Drawing tools

Pen, 12 colors, adjustable size
Laser pointer, fades after ~2.5s, good for presentations
Highlighter, semi-transparent, 4 preset colors
Pressure-sensitive width based on hand speed
Galaxy brush, just because it looked cool

Smart canvas stuff

Shape recognition, snaps wobbly circles/rectangles/triangles/lines into clean geometry
OCR, turns handwritten strokes into editable text via Tesseract
Grid templates: lined, graph, dot grid, music staff, Cornell notes

Advanced bits

Offline voice commands via Vosk, "undo", "clear", "color red", nothing leaves your machine
Gesture calibration wizard for different hand sizes
50-step undo/redo history
Export to PNG, PDF, or SVG
Save/load workspace as native .air files

The UI
Dark, minimal, inspired by Linear, Apple, and Notion. Inter font, restrained colors, consistent 8px spacing
 
## Running it locally
 
You'll need Python 3 and a webcam.
 
**1. Clone it**
```
git clone https://github.com/pk2010-ux/AirWriteStudio.git
cd AirWriteStudio
```
 
**2. Create a virtual environment** (technically optional but you will thank yourself later)
```
python -m venv venv
 
# Windows
venv\Scripts\activate
 
# macOS/Linux
source venv/bin/activate
```
 
**3. Install dependencies**
```
pip install -r requirements.txt
```
This pulls in OpenCV, MediaPipe, PyQt6, NumPy, SciPy, pytesseract, Vosk, qtawesome, and sounddevice. Yes, that's the voice and OCR libraries too, they're installed by default now rather than being a separate optional step, the code just quietly disables those features if something's missing instead of crashing, so you dont strictly have to set them up if you dont care about voice commands or OCR.
 
**4. OCR needs one more thing**
`pytesseract` is just a Python wrapper, the actual OCR engine has to be installed separately on your system: [Tesseract OCR](https://github.com/tesseract-ocr/tesseract). Without it, "convert to text" simply wont show up as usable.
 
**5. Voice commands should just work**
The Vosk speech model is already bundled in `assets/vosk-model`, so unlike what I used to tell people, you dont need to hunt down and download a model yourself anymore. If you have a working microphone, offline voice commands should work out of the box.
 
**6. Run it**
```
python main.py
```
Click Start Camera in the sidebar, hold your hand up, and try the gestures above. If nothing happens, check that your webcam isnt already in use by another app, that one gets me more often than Id like to admit.
 
## The second method
 
If setting up Python sounds like a chore, theres a prebuilt Windows executable under [Releases](https://github.com/pk2010-ux/AirWriteStudio/releases/tag/v1.0.0). Download it, run it, no install step required.
 
If you want to build that executable yourself instead of trusting a random .exe off the internet (fair honestly):
```
pip install pyinstaller
.\build.ps1
```
This spits out a bundled app at `dist\AirWriteStudio.exe`.
 
## Keyboard shortcuts
 
- `Ctrl+Z` — Undo
- `Ctrl+Y` — Redo
- `Ctrl+S` — Save as PNG
- `Ctrl+E` — Export as PDF
- `Ctrl+N` — Clear canvas
- `F11` — Toggle fullscreen
- `Home` — Reset zoom/pan view
## How it works
 
The gesture detection isnt just "is your thumb near your index finger, yes/no." Every distance between fingertips gets normalized against your palm size first, so it works whether youre a foot away from the camera or right up close, and whether your hands are big or small. On top of that there's hysteresis on every threshold (basically two different trigger points for turning a gesture on versus off) plus frame-by-frame debouncing before a gesture is accepted as "real". I added all of that after the early version kept flickering between pen and neutral mode if my hand so much as twitched, which made drawing a straight line feel like trying to write during an earthquake.
 
The undo/redo system in `canvas_engine.py` caps out at 50 steps, past that it starts dropping the oldest actions rather than eating memory forever. Laser pointer strokes are the one exception, they arent pushed onto the undo stack at all since they're meant to fade and disappear anyway.
 
Both OCR and voice commands are wrapped in try/except import guards, so if Tesseract isnt installed on your system, or your mic setup is broken, the app still launches fine, it just quietly turns those specific features off instead of crashing on startup. I didnt want one missing dependency to take down the entire app.
## Contributing
 
Contributions, issues, and feature requests are welcome, check the [issues page](https://github.com/pk2010-ux/AirWriteStudio/issues).
 
## Guide used
 
[Writing a README that doesn't suck](https://stardance.hackclub.com/resources/great_readme) — used this to structure this exact file, if this README is actually decent, credit goes there
 
## License
 
This project is Licensed under MIT.
