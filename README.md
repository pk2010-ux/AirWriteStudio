# AirWrite Studio

A hands-free digital canvas that lets you draw, erase, and annotate using nothing but your hand in front of a webcam, no mouse, no stylus, no touching anything

![Image](/image.png)

**AirWrite Studio** is a real-time, camera-based drawing app. Point a normal webcam at your hand, pinch your fingers together, and start drawing in mid-air like some kind of wizard who also happens to know Python. It uses MediaPipe to track your hand and turns specific finger positions into canvas actions. The first time it actually worked for me I got way too excited and startled my own cat off the desk.

## Try it

There's a browser demo running on Hugging Face Spaces if you just want to poke it without installing anything: [Try it here](https://huggingface.co/spaces/Priyajit0202/AWS-demo)

Heads up though, the web version runs the hand-tracking on the server instead of on your machine, so depending on your connection and how busy the server is, it can lag or get a little glitchy. If it feels laggy that isnt your webcam being bad, its just the nature of doing MediaPipe over a network instead of locally. The desktop version below doesnt have that problem since everything runs on your own machine.

There's also a prebuilt Windows executable if you dont want to touch Python at all, see "the second method" further down. Mac and Linux dont have a prebuilt binary yet, but you can build one yourself with a couple commands, also covered below.

## Quick start

If you just want to see it work: use the demo link above, give it camera access, and pinch your thumb and index finger together over the canvas.

If you want the real, non-laggy experience, pick your OS below, it is a handful of terminal commands either way.

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

**Drawing tools**
- Pen, 12 colors, adjustable size
- Laser pointer, fades after ~2.5s, good for presentations
- Highlighter, semi-transparent, 4 preset colors
- Pressure-sensitive width based on hand speed
- Galaxy brush, just because it looked cool

**Smart canvas stuff**
- Shape recognition, snaps wobbly circles/rectangles/triangles/lines into clean geometry
- OCR, turns handwritten strokes into editable text via Tesseract
- Grid templates: lined, graph, dot grid, music staff, Cornell notes

**Advanced bits**
- Offline voice commands via Vosk, "undo", "clear", "color red", nothing leaves your machine
- Gesture calibration wizard for different hand sizes
- 50-step undo/redo history
- Export to PNG, PDF, or SVG
- Save/load workspace as native `.air` files

**The UI**
Dark, minimal, inspired by Linear, Apple, and Notion. Inter font, restrained colors, consistent 8px spacing

## Installing it

This used to be a Windows-only app, I hadnt tested it anywhere else and there were a few Windows-specific assumptions baked in without me realizing. Its cross-platform now, each OS gets its own requirements file with the right system-level notes attached, pick yours below.

### Windows

**1. Clone it**
```
git clone https://github.com/pk2010-ux/AirWriteStudio.git
cd AirWriteStudio
```

**2. Create a virtual environment** (optional but you will thank yourself later)
```
python -m venv venv
venv\Scripts\activate
```

**3. Install dependencies**
```
pip install -r win_requirements.txt
```

**4. Install Tesseract separately if you want OCR**
`pytesseract` is just a wrapper, the actual engine needs installing on your system: [Tesseract OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki). Make sure you tick "add to PATH" during setup, or the app wont find it.

**5. Voice commands should just work out of the box**
The Vosk speech model is already bundled in `assets/`, no separate download needed.

**6. Run it**
```
python main.py
```

### macOS

**1. Clone it**
```
git clone https://github.com/pk2010-ux/AirWriteStudio.git
cd AirWriteStudio
```

**2. Create a virtual environment**
```
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**
```
pip install -r requirements_macos.txt
```

**4. Install two system packages via Homebrew**
```
brew install tesseract portaudio
```
Tesseract is for OCR, PortAudio is what lets `sounddevice` actually talk to your microphone for voice commands. Skip either one and that specific feature just quietly turns itself off instead of crashing, so its not mandatory, just recommended.

**5. Run it**
```
python3 main.py
```

### Linux

**1. Install a few system libraries first**, PyQt6 wont even launch without these on most distros
```
sudo apt install libegl1 libgl1-mesa-glx libxcb-xinerama0 libxcb-cursor0
```

**2. Clone it**
```
git clone https://github.com/pk2010-ux/AirWriteStudio.git
cd AirWriteStudio
```

**3. Create a virtual environment**
```
python3 -m venv venv
source venv/bin/activate
```

**4. Install dependencies**
```
pip install -r requirements_linux.txt
```

**5. Install OCR and voice system packages**
```
sudo apt install tesseract-ocr libportaudio2
```
Same deal as macOS, both are optional, the app just runs with those features disabled if youd rather skip them.

**6. Run it**
```
python3 main.py
```

*(Commands above assume Debian/Ubuntu with apt. If youre on Fedora, Arch, or something else, swap in your distro's package manager, the package names are usually close enough to guess.)*

Not fussed about picking the exact right file for your OS? `requirements.txt` is the universal one, same packages, works everywhere, it just doesnt come with the OS-specific system dependency notes in the comments the way the platform files do.

## The second method

**Windows**: theres a prebuilt executable under [Releases](https://github.com/pk2010-ux/AirWriteStudio/releases/tag/v1.0.0), download it and run it, no Python needed. To build it yourself instead:
```
pip install pyinstaller
.\build.ps1
```
This spits out a bundled app at `dist\AirWriteStudio.exe`.

**macOS / Linux**: no prebuilt binary yet, but `build.sh` does the same job:
```
chmod +x build.sh
./build.sh
```
This uses the same PyInstaller flags as the Windows build, just with `:` instead of `;` as the data separator, since apparently that one character is where Windows and everything else disagree.

## If something breaks

Packaged builds dont show a console window, so if the camera or model fails to start, it can look like the app just silently quit. It didnt, it wrote a log first. Check here depending on your OS:

- **Windows**: `%LOCALAPPDATA%\AirWrite Studio\airwrite.log`
- **macOS**: `~/Library/Application Support/AirWrite Studio/airwrite.log`
- **Linux**: `$XDG_DATA_HOME/AirWrite Studio/airwrite.log` (or `~/.local/share/AirWrite Studio/airwrite.log` if that env var isnt set)

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

Getting this running outside Windows meant finding every place I had quietly assumed Windows without meaning to. Turned out there were three of them: the camera backend was hardcoded to DirectShow which straight up doesnt exist on Linux or macOS, the log directory used `LOCALAPPDATA` which is a Windows-only environment variable, and the UI font was hardcoded to Segoe UI, which looks fine on Windows and looks like a fallback system font everywhere else. All three are handled by a couple of small platform checks now, `config.py` picks the right UI and emoji font per OS, `app_logging.py` picks the right log directory per OS, and the camera backend only forces DirectShow when it detects Windows. Nothing fancy, I just hadnt needed to think about it until I actually tried running this on a Mac.

## Contributing

Contributions, issues, and feature requests are welcome, check the [issues page](https://github.com/pk2010-ux/AirWriteStudio/issues).

## Guide used

[Writing a README that doesn't suck](https://stardance.hackclub.com/resources/great_readme) — used this to structure this exact file, if this README is actually decent, credit goes there

## License

MIT — Copyright (c) 2026 Priyajit Kundu, see the `LICENSE` file for the full text
