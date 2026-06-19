"""
AirWrite Studio - Voice Commander
====================================
Offline voice command processor using the Vosk speech recognition library.
Runs audio capture and recognition in a background QThread, emitting parsed
commands via Qt signals.  All heavy dependencies (vosk, pyaudio) are
lazily imported so the rest of the application can still start even when
they are not installed.
"""

import json
import os
import time
import queue
import sys
from typing import ClassVar, Dict, Optional, Tuple

from PyQt6.QtCore import QThread, pyqtSignal
from utils import get_resource_path


# ─── Optional Dependency Guard ──────────────────────────────────────────────

try:
    import vosk          # type: ignore[import-untyped]
    import sounddevice as sd
    _VOSK_AVAILABLE = True
except ImportError:
    _VOSK_AVAILABLE = False


# ─── Color Map ───────────────────────────────────────────────────────────────

COLOR_MAP: Dict[str, str] = {
    'red':    '#FF6B6B',
    'blue':   '#45B7D1',
    'white':  '#FFFFFF',
    'green':  '#96CEB4',
    'yellow': '#FFEAA7',
    'orange': '#FF8C42',
    'purple': '#BB8FCE',
    'pink':   '#DDA0DD',
    'teal':   '#4ECDC4',
    'black':  '#333333',
}


# ─── Audio Constants ─────────────────────────────────────────────────────────

_SAMPLE_RATE: int = 16000
_CHANNELS: int = 1
_COMMAND_COOLDOWN: float = 1.5   # seconds between accepted commands


# ─── Voice Commander Thread ─────────────────────────────────────────────────

class VoiceCommander(QThread):
    """
    Background thread that captures microphone audio via sounddevice,
    runs Vosk offline speech recognition, and translates recognized
    phrases into application commands via simple keyword matching.
    """

    # ── Qt Signals ───────────────────────────────────────────────────────
    command_recognized = pyqtSignal(str, dict)
    status_changed     = pyqtSignal(str)
    listening_started  = pyqtSignal()
    listening_stopped  = pyqtSignal()

    # ── Model path (relative to project root / assets) ───────────────────
    _MODEL_DIR: ClassVar[str] = get_resource_path(os.path.join(
        'assets',
        'vosk-model',
    ))

    # ── Command vocabulary ───────────────────────────────────────────────
    _COMMAND_TABLE: ClassVar[list[Tuple[Tuple[str, ...], str, dict]]] = [
        (('clear canvas', 'clear'),          'clear',      {}),
        (('undo',),                          'undo',       {}),
        (('redo',),                          'redo',       {}),
        (('save',),                          'save',       {}),
        (('zoom in',),                       'zoom',       {'direction': 'in'}),
        (('zoom out',),                      'zoom',       {'direction': 'out'}),
        (('reset view', 'reset zoom'),       'reset_view', {}),
        (('highlighter',),                   'tool',       {'tool': 'highlighter'}),
        (('eraser',),                        'tool',       {'tool': 'eraser'}),
        (('laser pointer', 'laser'),         'tool',       {'tool': 'laser'}),
        (('pen',),                           'tool',       {'tool': 'pen'}),
        (('thick brush', 'big brush'),       'pen_size',   {'size': 8.0}),
        (('thin brush', 'small brush'),      'pen_size',   {'size': 2.0}),
        (('normal brush', 'medium brush'),   'pen_size',   {'size': 4.0}),
    ]

    def __init__(self, parent: Optional[object] = None) -> None:
        super().__init__(parent)
        self._running: bool = False
        self._last_command_time: float = 0.0
        self._audio_queue = queue.Queue()

    @classmethod
    def is_available(cls) -> bool:
        return _VOSK_AVAILABLE

    def stop(self) -> None:
        self._running = False
        # Add a dummy byte to queue to unblock the thread
        self._audio_queue.put(b"")
        self.wait(3000)

    def _audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        self._audio_queue.put(bytes(indata))

    def run(self) -> None:
        if not _VOSK_AVAILABLE:
            self.status_changed.emit('Vosk / sounddevice not installed')
            return

        if not os.path.isdir(self._MODEL_DIR):
            self.status_changed.emit('Model not found')
            return

        self.status_changed.emit('Loading model…')
        try:
            vosk.SetLogLevel(-1)
            model = vosk.Model(self._MODEL_DIR)
        except Exception as exc:
            self.status_changed.emit(f'Error loading model: {exc}')
            return

        recognizer = vosk.KaldiRecognizer(model, _SAMPLE_RATE)
        self._running = True
        self._last_command_time = 0.0

        self.status_changed.emit('Starting microphone…')
        try:
            with sd.RawInputStream(samplerate=_SAMPLE_RATE, blocksize=8000,
                                   dtype='int16', channels=_CHANNELS,
                                   callback=self._audio_callback):
                
                self.status_changed.emit('Listening…')
                self.listening_started.emit()

                while self._running:
                    data = self._audio_queue.get()
                    if not self._running:
                        break
                    
                    if len(data) == 0:
                        continue
                        
                    if recognizer.AcceptWaveform(data):
                        result_json = recognizer.Result()
                        self._handle_result(result_json)
                        
        except Exception as exc:
            self.status_changed.emit(f'Microphone error: {exc}')
        finally:
            self.listening_stopped.emit()
            self.status_changed.emit('Stopped')

    def _handle_result(self, result_json: str) -> None:
        try:
            data = json.loads(result_json)
        except json.JSONDecodeError:
            return

        text: str = data.get('text', '').strip().lower()
        if not text:
            return

        self.status_changed.emit('Processing…')
        command, params = self._match_command(text)
        if command is not None:
            now = time.monotonic()
            if now - self._last_command_time >= _COMMAND_COOLDOWN:
                self._last_command_time = now
                self.command_recognized.emit(command, params)

        self.status_changed.emit('Listening…')

    def _match_command(self, text: str) -> Tuple[Optional[str], dict]:
        if text.startswith('color') or text.startswith('colour'):
            for colour_name, hex_code in COLOR_MAP.items():
                if colour_name in text:
                    return 'color', {'color': hex_code}

        for phrases, cmd, params in self._COMMAND_TABLE:
            for phrase in phrases:
                if phrase in text:
                    return cmd, dict(params)

        return None, {}
