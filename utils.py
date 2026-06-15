"""
AirWrite Studio - Utility Functions
====================================
Shared utility functions for coordinate conversion, distance calculation,
and image format conversion used across modules.
"""

import math
import numpy as np
import cv2
from PyQt6.QtGui import QImage
from PyQt6.QtCore import QPointF


def distance(p1, p2):
    """
    Euclidean distance between two points.
    
    Args:
        p1: Tuple (x, y) or object with .x and .y attributes
        p2: Tuple (x, y) or object with .x and .y attributes
    
    Returns:
        float: Euclidean distance
    """
    if hasattr(p1, 'x') and callable(getattr(p1, 'x', None)):
        # QPointF style
        return math.sqrt((p1.x() - p2.x()) ** 2 + (p1.y() - p2.y()) ** 2)
    elif hasattr(p1, 'x'):
        # MediaPipe landmark style
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)
    else:
        # Tuple style
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def landmark_distance(landmarks, id1, id2):
    """
    Euclidean distance between two MediaPipe landmarks (normalized coords).
    
    Args:
        landmarks: List of NormalizedLandmark (new Tasks API format)
        id1: First landmark index
        id2: Second landmark index
    
    Returns:
        float: Normalized euclidean distance
    """
    lm1 = landmarks[id1]
    lm2 = landmarks[id2]
    return math.sqrt((lm1.x - lm2.x) ** 2 + (lm1.y - lm2.y) ** 2)


def get_palm_size(landmarks):
    """
    Get palm size as reference for scale-invariant gesture thresholds.
    Measured as distance from wrist (0) to middle finger MCP (9).
    
    Args:
        landmarks: List of NormalizedLandmark
    
    Returns:
        float: Normalized palm size
    """
    return landmark_distance(landmarks, 0, 9)


def midpoint(p1, p2):
    """
    Midpoint between two points.
    
    Args:
        p1: Tuple (x, y)
        p2: Tuple (x, y)
    
    Returns:
        Tuple (x, y): Midpoint
    """
    return ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)


def landmark_to_pixel(landmark, canvas_width, canvas_height):
    """
    Convert a MediaPipe normalized landmark (0-1) to canvas pixel coordinates.
    
    Args:
        landmark: MediaPipe landmark with .x and .y attributes (0-1 range)
        canvas_width: Canvas width in pixels
        canvas_height: Canvas height in pixels
    
    Returns:
        Tuple (x, y): Pixel coordinates
    """
    return (landmark.x * canvas_width, landmark.y * canvas_height)


def landmark_to_qpoint(landmark, canvas_width, canvas_height):
    """
    Convert a MediaPipe normalized landmark to a QPointF on the canvas.
    
    Args:
        landmark: MediaPipe landmark with .x and .y attributes (0-1 range)
        canvas_width: Canvas width in pixels
        canvas_height: Canvas height in pixels
    
    Returns:
        QPointF: Point in canvas coordinates
    """
    return QPointF(landmark.x * canvas_width, landmark.y * canvas_height)


def qimage_from_cv(frame):
    """
    Convert an OpenCV BGR frame to a QImage (RGB888 format).
    
    The returned QImage owns a copy of the pixel data, so it remains
    valid even after the original OpenCV frame buffer is overwritten.
    
    Args:
        frame: OpenCV BGR numpy array (H x W x 3)
    
    Returns:
        QImage: Converted image in RGB888 format
    """
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_frame.shape
    bytes_per_line = ch * w
    qt_image = QImage(
        rgb_frame.data, w, h, bytes_per_line,
        QImage.Format.Format_RGB888
    ).copy()  # .copy() ensures data persists after frame buffer is overwritten
    return qt_image


def is_finger_extended(landmarks, finger_tip_id):
    """
    Check if a non-thumb finger is extended by comparing tip Y to PIP Y.
    In image coordinates, smaller Y = higher position = finger pointing up.
    
    Args:
        landmarks: List of NormalizedLandmark
        finger_tip_id: Landmark index of the finger tip (8, 12, 16, or 20)
    
    Returns:
        bool: True if finger is extended (pointing up)
    """
    tip = landmarks[finger_tip_id]
    pip = landmarks[finger_tip_id - 2]
    return tip.y < pip.y


def is_thumb_extended(landmarks):
    """
    Check if thumb is extended. Thumb extends horizontally,
    so we compare X coordinates instead of Y.
    Uses the mirrored/webcam convention (right hand appears on left).
    
    Args:
        landmarks: List of NormalizedLandmark
    
    Returns:
        bool: True if thumb is extended
    """
    thumb_tip = landmarks[4]
    thumb_ip = landmarks[3]
    # In mirrored view, extended thumb tip is further from palm center
    # We use absolute distance from MCP to determine extension
    thumb_mcp = landmarks[2]
    dist_tip_mcp = math.sqrt((thumb_tip.x - thumb_mcp.x) ** 2 + (thumb_tip.y - thumb_mcp.y) ** 2)
    dist_ip_mcp = math.sqrt((thumb_ip.x - thumb_mcp.x) ** 2 + (thumb_ip.y - thumb_mcp.y) ** 2)
    return dist_tip_mcp > dist_ip_mcp * 1.2
