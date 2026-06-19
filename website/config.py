"""
AirWrite Studio - Configuration & Constants
============================================
Central configuration for gesture thresholds, smoothing parameters,
camera settings, canvas defaults, and UI constants.
"""

from enum import Enum


# ─── Gesture Modes ───────────────────────────────────────────────────────────

class GestureMode(Enum):
    """Available gesture modes for the application."""
    NEUTRAL = "neutral"
    PEN = "pen"
    ERASER = "eraser"
    SELECT = "select"
    DRAG = "drag"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"


# ─── Gesture Thresholds (scale-invariant, relative to palm size) ─────────────

# Pinch detection: thumb tip to index tip distance / palm size
# Made generous — pinch is the PRIMARY gesture, must be easy to trigger
PINCH_THRESHOLD_ACTIVATE = 0.35      # Enter pinch state (was 0.25)
PINCH_THRESHOLD_DEACTIVATE = 0.65    # Exit pinch state — wide hysteresis gap

# Two-finger together: index tip to middle tip distance / palm size
# Made TIGHT to avoid false eraser triggers during pen mode
TWO_FINGER_THRESHOLD_ACTIVATE = 0.12   # Much tighter (was 0.20)
TWO_FINGER_THRESHOLD_DEACTIVATE = 0.22 # (was 0.30)

# Three-finger pinch: all three tips close / palm size
THREE_FINGER_THRESHOLD_ACTIVATE = 0.28
THREE_FINGER_THRESHOLD_DEACTIVATE = 0.40

# Open palm: minimum spread between index and pinky tips / palm size
OPEN_PALM_SPREAD_THRESHOLD = 0.6      # Stricter (was 0.5)

# Zoom In gesture: Thumb + Middle pinch thresholds
ZOOM_IN_PINCH_ACTIVATE = 0.30
ZOOM_IN_PINCH_DEACTIVATE = 0.45

# Zoom Out gesture: Thumb + Ring pinch thresholds
ZOOM_OUT_PINCH_ACTIVATE = 0.30
ZOOM_OUT_PINCH_DEACTIVATE = 0.45

# ─── Gesture Stability ──────────────────────────────────────────────────────

GESTURE_STABILITY_FRAMES = 5    # Frames before confirming a gesture change (was 3)
GESTURE_BUFFER_SIZE = 7         # Rolling buffer size for gesture history

# Extra stability: frames required to LEAVE pen mode (higher = stickier pen)
PEN_EXIT_FRAMES = 5             # Increased to prevent lines breaking mid-stroke (was 2)

# ─── Tracking & Smoothing Config ───────────────────────────────────────────

SMOOTHING_MIN_CUTOFF = 0.1    # Lower = more smoothing at slow speeds (was 0.5)
SMOOTHING_BETA = 0.002        # Higher = less smoothing at high speeds (was 0.005)
SMOOTHING_D_CUTOFF = 1.0      # Derivative cutoff
JITTER_THRESHOLD = 1.5        # Pixel threshold to ignore tiny hand tremors

# ─── Canvas Defaults ─────────────────────────────────────────────────────────

CANVAS_BACKGROUND_COLOR = '#161616' # Dark neutral canvas
DEFAULT_PEN_COLOR = '#EDEDED'       # Near-white default pen
DEFAULT_PEN_SIZE = 4.0          # pixels
MIN_PEN_SIZE = 1.0
MAX_PEN_SIZE = 20.0

DEFAULT_ERASER_SIZE = 20.0      # pixels
MIN_ERASER_SIZE = 5.0
MAX_ERASER_SIZE = 50.0

# Color palette for quick selection
COLOR_PALETTE = [
    "#FFFFFF",  # White
    "#FF6B6B",  # Coral Red
    "#4ECDC4",  # Teal
    "#45B7D1",  # Sky Blue
    "#96CEB4",  # Sage Green
    "#FFEAA7",  # Pale Yellow
    "#DDA0DD",  # Plum
    "#FF8C42",  # Orange
    "#98D8C8",  # Mint
    "#F7DC6F",  # Gold
    "#BB8FCE",  # Lavender
    "#85C1E9",  # Light Blue
]

# ─── Laser Pointer Mode ─────────────────────────────────────────────────────

LASER_FADE_DURATION = 2.5       # Seconds before laser strokes fully fade
LASER_COLOR = "#FF4444"         # Bright red (classic laser pointer)
LASER_WIDTH = 4.0               # Pixels
LASER_GLOW_RADIUS = 12.0        # Glow effect radius around laser strokes

# ─── Highlighter Brush ──────────────────────────────────────────────────────

HIGHLIGHTER_ALPHA = 80          # Opacity out of 255
HIGHLIGHTER_WIDTH = 20.0        # Default highlighter width
HIGHLIGHTER_COLORS = [
    "#FFFF00",  # Yellow
    "#00FF7F",  # Spring Green
    "#FF69B4",  # Hot Pink
    "#87CEEB",  # Sky Blue
]

# ─── Dynamic Speed-Based Width ───────────────────────────────────────────────

DYNAMIC_WIDTH_MAX_SPEED = 800.0     # px/sec — strokes thinnest above this
DYNAMIC_WIDTH_MIN_FACTOR = 0.3      # Minimum width as fraction of base pen size
DYNAMIC_WIDTH_MAX_FACTOR = 2.0      # Maximum width as fraction of base pen size

# ─── Shape Recognition ──────────────────────────────────────────────────────

SHAPE_MIN_POINTS = 10               # Minimum stroke points to attempt recognition
SHAPE_LINE_R2_THRESHOLD = 0.90      # Linear fit R² threshold
SHAPE_CIRCULARITY_THRESHOLD = 0.25  # Max std_dev/mean ratio for circle
SHAPE_RECT_ANGLE_TOLERANCE = 25.0   # Degrees tolerance for 90° corners
SHAPE_CLOSURE_THRESHOLD = 0.35      # Start-to-end distance / diameter ratio

# ─── Zoom & Pan (Object Scaling) ─────────────────────────────────────────────

OBJECT_SCALE_MIN = 0.25         # Minimum scale for an object
OBJECT_SCALE_MAX = 4.0          # Maximum scale for an object
OBJECT_SCALE_SPEED = 0.02       # Scale delta per frame when zooming

# ─── Voice Commands ─────────────────────────────────────────────────────────

import os as _os
VOSK_MODEL_DIR = _os.path.join(
    _os.path.dirname(__file__), "assets", "vosk-model"
)
VOICE_COMMAND_COOLDOWN = 1.5    # Seconds between recognized commands

VOICE_COLOR_MAP = {
    "red": "#FF6B6B",
    "blue": "#45B7D1",
    "white": "#FFFFFF",
    "green": "#96CEB4",
    "yellow": "#FFEAA7",
    "orange": "#FF8C42",
    "purple": "#BB8FCE",
    "pink": "#DDA0DD",
    "teal": "#4ECDC4",
    "black": "#333333",
}

# ─── Camera Settings ─────────────────────────────────────────────────────────

CAMERA_INDEX = 0                # Default webcam index
CAMERA_WIDTH = 1280             # Target resolution width
CAMERA_HEIGHT = 720             # Target resolution height
CAMERA_FPS_TARGET = 30          # Target frames per second

# MediaPipe Hands configuration
MP_MAX_NUM_HANDS = 1
MP_MODEL_COMPLEXITY = 0         # 0=fast, 1=accurate (Set to 0 for huge FPS boost)
MP_MIN_DETECTION_CONFIDENCE = 0.7
MP_MIN_TRACKING_CONFIDENCE = 0.5

# ─── UI Constants ────────────────────────────────────────────────────────────

SIDEBAR_WIDTH = 340             # Fixed sidebar width in pixels
CAMERA_PREVIEW_WIDTH = 250      # Camera preview width in sidebar
CAMERA_PREVIEW_HEIGHT = 188     # Camera preview height (4:3 aspect)

WINDOW_MIN_WIDTH = 1100
WINDOW_MIN_HEIGHT = 700
WINDOW_DEFAULT_WIDTH = 1400
WINDOW_DEFAULT_HEIGHT = 850

# ─── Undo/Redo ───────────────────────────────────────────────────────────────

MAX_UNDO_STEPS = 50

# ─── MediaPipe Landmark Indices ──────────────────────────────────────────────

# Named constants for readability (matching mp.solutions.hands.HandLandmark)
LM_WRIST = 0
LM_THUMB_CMC = 1
LM_THUMB_MCP = 2
LM_THUMB_IP = 3
LM_THUMB_TIP = 4
LM_INDEX_MCP = 5
LM_INDEX_PIP = 6
LM_INDEX_DIP = 7
LM_INDEX_TIP = 8
LM_MIDDLE_MCP = 9
LM_MIDDLE_PIP = 10
LM_MIDDLE_DIP = 11
LM_MIDDLE_TIP = 12
LM_RING_MCP = 13
LM_RING_PIP = 14
LM_RING_DIP = 15
LM_RING_TIP = 16
LM_PINKY_MCP = 17
LM_PINKY_PIP = 18
LM_PINKY_DIP = 19
LM_PINKY_TIP = 20

# ─── Gesture Mode Display Info ───────────────────────────────────────────────

GESTURE_MODE_INFO = {
    GestureMode.NEUTRAL: {
        "label": "Neutral",
        "color": "#555555",
        "icon": "",
        "description": "Open palm — no action"
    },
    GestureMode.PEN: {
        "label": "Drawing",
        "color": "#0091FF",
        "icon": "",
        "description": "Thumb + Index pinch — draw"
    },
    GestureMode.ERASER: {
        "label": "Erasing",
        "color": "#E5484D",
        "icon": "",
        "description": "Closed fist + thumb out — erase"
    },
    GestureMode.SELECT: {
        "label": "Select",
        "color": "#AB6400",
        "icon": "",
        "description": "Index finger point — select"
    },
    GestureMode.DRAG: {
        "label": "Dragging",
        "color": "#AB6400",
        "icon": "",
        "description": "Three fingers — drag selected"
    },
    GestureMode.ZOOM_IN: {
        "label": "Zoom In",
        "color": "#46A758",
        "icon": "",
        "description": "Thumb + Middle — scale up"
    },
    GestureMode.ZOOM_OUT: {
        "label": "Zoom Out",
        "color": "#46A758",
        "icon": "",
        "description": "Thumb + Ring — scale down"
    },
}
