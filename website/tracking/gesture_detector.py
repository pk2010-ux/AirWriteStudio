"""
AirWrite Studio - Gesture Detector
====================================
Classifies hand landmarks from MediaPipe into gesture modes using
scale-invariant thresholds, hysteresis, and frame-based debouncing
for stable, flicker-free gesture recognition.

Gesture definitions (strict finger requirements):
  PEN:     Thumb + Index pinched  AND  middle + ring fingers OPEN
  ERASER:  All 4 fingers curled   AND  thumb extended (thumbs-up fist)
  DRAG:    Thumb + Index + Middle all pinched together
  SELECT:  Only index finger pointing up, others down
  ZOOM_IN: Thumb + Middle pinched AND others open
  ZOOM_OUT: Thumb + Ring pinched AND others open
  NEUTRAL: Open palm / default
"""

from collections import deque

from config import (
    GestureMode,
    PINCH_THRESHOLD_ACTIVATE, PINCH_THRESHOLD_DEACTIVATE,
    THREE_FINGER_THRESHOLD_ACTIVATE, THREE_FINGER_THRESHOLD_DEACTIVATE,
    OPEN_PALM_SPREAD_THRESHOLD,
    ZOOM_IN_PINCH_ACTIVATE, ZOOM_IN_PINCH_DEACTIVATE,
    ZOOM_OUT_PINCH_ACTIVATE, ZOOM_OUT_PINCH_DEACTIVATE,
    GESTURE_STABILITY_FRAMES, GESTURE_BUFFER_SIZE, PEN_EXIT_FRAMES,
    LM_THUMB_TIP, LM_INDEX_TIP, LM_MIDDLE_TIP, LM_RING_TIP, LM_PINKY_TIP,
    LM_INDEX_MCP, LM_MIDDLE_MCP, LM_RING_MCP, LM_PINKY_MCP,
)
from utils import landmark_distance, get_palm_size, is_finger_extended, is_thumb_extended


class HysteresisThreshold:
    """
    Prevents flickering when a measured value hovers near a threshold.
    Uses separate activate/deactivate thresholds with a dead zone.
    """

    def __init__(self, activate: float, deactivate: float):
        self.activate = activate
        self.deactivate = deactivate
        self.active = False

    def update(self, value: float) -> bool:
        if not self.active and value < self.activate:
            self.active = True
        elif self.active and value > self.deactivate:
            self.active = False
        return self.active

    def reset(self):
        self.active = False


class GestureDetector:
    """
    Classifies hand landmarks into gesture modes with stability.
    """

    def __init__(self):
        # Hysteresis thresholds
        self._pinch_threshold = HysteresisThreshold(
            PINCH_THRESHOLD_ACTIVATE, PINCH_THRESHOLD_DEACTIVATE
        )
        self._three_finger_threshold = HysteresisThreshold(
            THREE_FINGER_THRESHOLD_ACTIVATE, THREE_FINGER_THRESHOLD_DEACTIVATE
        )
        self._zoom_in_threshold = HysteresisThreshold(
            ZOOM_IN_PINCH_ACTIVATE, ZOOM_IN_PINCH_DEACTIVATE
        )
        self._zoom_out_threshold = HysteresisThreshold(
            ZOOM_OUT_PINCH_ACTIVATE, ZOOM_OUT_PINCH_DEACTIVATE
        )

        # Frame-based debouncing
        self._gesture_buffer = deque(maxlen=GESTURE_BUFFER_SIZE)
        self._current_gesture = GestureMode.NEUTRAL
        self._pending_gesture = GestureMode.NEUTRAL
        self._pending_count = 0
        self._stability_frames = GESTURE_STABILITY_FRAMES

        # Track whether objects are selected
        self.has_selection = False

    def detect(self, landmarks) -> tuple[GestureMode, tuple[float, float]]:
        palm_size = get_palm_size(landmarks)
        if palm_size < 0.01:
            return self._current_gesture, (0.5, 0.5)

        # ─── Compute normalized distances ─────────────────────────
        d_thumb_index = landmark_distance(landmarks, LM_THUMB_TIP, LM_INDEX_TIP) / palm_size
        d_index_middle = landmark_distance(landmarks, LM_INDEX_TIP, LM_MIDDLE_TIP) / palm_size
        d_thumb_middle = landmark_distance(landmarks, LM_THUMB_TIP, LM_MIDDLE_TIP) / palm_size
        d_thumb_ring = landmark_distance(landmarks, LM_THUMB_TIP, LM_RING_TIP) / palm_size

        # ─── Check finger extension states ────────────────────────
        index_up = is_finger_extended(landmarks, LM_INDEX_TIP)
        middle_up = is_finger_extended(landmarks, LM_MIDDLE_TIP)
        ring_up = is_finger_extended(landmarks, LM_RING_TIP)
        pinky_up = is_finger_extended(landmarks, LM_PINKY_TIP)
        thumb_up = is_thumb_extended(landmarks)

        other_fingers_up = sum([middle_up, ring_up, pinky_up])

        # ─── Update hysteresis thresholds ─────────────────────────
        pinch_active = self._pinch_threshold.update(d_thumb_index)
        three_finger_dist = max(d_thumb_index, d_index_middle, d_thumb_middle)
        three_finger_active = self._three_finger_threshold.update(three_finger_dist)
        zoom_in_active = self._zoom_in_threshold.update(d_thumb_middle)
        zoom_out_active = self._zoom_out_threshold.update(d_thumb_ring)

        # ─── Reference landmarks ─────────────────────────────────
        index_tip = landmarks[LM_INDEX_TIP]
        middle_tip = landmarks[LM_MIDDLE_TIP]
        ring_tip = landmarks[LM_RING_TIP]
        thumb_tip = landmarks[LM_THUMB_TIP]
        action_point = (index_tip.x, index_tip.y)

        # ─── Gesture Classification ──────────────────────────────
        raw_gesture = GestureMode.NEUTRAL

        if three_finger_active:
            raw_gesture = GestureMode.DRAG
            action_point = (
                (thumb_tip.x + index_tip.x + middle_tip.x) / 3.0,
                (thumb_tip.y + index_tip.y + middle_tip.y) / 3.0,
            )

        # Thumb + Middle pinch -> ZOOM IN
        elif zoom_in_active and index_up and ring_up and pinky_up:
            raw_gesture = GestureMode.ZOOM_IN
            action_point = (
                (middle_tip.x + thumb_tip.x) / 2.0,
                (middle_tip.y + thumb_tip.y) / 2.0,
            )

        # Thumb + Ring pinch -> ZOOM OUT
        elif zoom_out_active and index_up and middle_up and pinky_up:
            raw_gesture = GestureMode.ZOOM_OUT
            action_point = (
                (ring_tip.x + thumb_tip.x) / 2.0,
                (ring_tip.y + thumb_tip.y) / 2.0,
            )

        elif pinch_active and other_fingers_up >= 2:
            raw_gesture = GestureMode.PEN
            action_point = (
                (index_tip.x + thumb_tip.x) / 2.0,
                (index_tip.y + thumb_tip.y) / 2.0,
            )

        elif (thumb_up
              and not index_up and not middle_up
              and not ring_up and not pinky_up):
            raw_gesture = GestureMode.ERASER
            idx_mcp = landmarks[LM_INDEX_MCP]
            mid_mcp = landmarks[LM_MIDDLE_MCP]
            ring_mcp = landmarks[LM_RING_MCP]
            pinky_mcp = landmarks[LM_PINKY_MCP]
            action_point = (
                (idx_mcp.x + mid_mcp.x + ring_mcp.x + pinky_mcp.x) / 4.0,
                (idx_mcp.y + mid_mcp.y + ring_mcp.y + pinky_mcp.y) / 4.0,
            )

        elif (index_up and middle_up and ring_up and pinky_up and thumb_up):
            palm_spread = landmark_distance(
                landmarks, LM_INDEX_TIP, LM_PINKY_TIP
            ) / palm_size
            if palm_spread > OPEN_PALM_SPREAD_THRESHOLD:
                raw_gesture = GestureMode.NEUTRAL

        elif (index_up and not middle_up and not ring_up and not pinky_up):
            raw_gesture = GestureMode.SELECT
            action_point = (index_tip.x, index_tip.y)

        else:
            raw_gesture = GestureMode.NEUTRAL

        # ─── Debouncing ──────────────────────────────────────────
        stable_gesture = self._stabilize(raw_gesture)

        return stable_gesture, action_point

    def _stabilize(self, detected: GestureMode) -> GestureMode:
        self._gesture_buffer.append(detected)

        if detected == self._current_gesture:
            self._pending_gesture = GestureMode.NEUTRAL
            self._pending_count = 0
            return self._current_gesture

        if detected == self._pending_gesture:
            self._pending_count += 1

            if (self._current_gesture == GestureMode.PEN
                    and detected == GestureMode.DRAG):
                required = 3
            elif self._current_gesture == GestureMode.PEN:
                required = PEN_EXIT_FRAMES
            else:
                required = self._stability_frames

            if self._pending_count >= required:
                self._current_gesture = detected
                self._pending_gesture = GestureMode.NEUTRAL
                self._pending_count = 0
        else:
            self._pending_gesture = detected
            self._pending_count = 1

        return self._current_gesture

    def reset(self):
        self._pinch_threshold.reset()
        self._three_finger_threshold.reset()
        self._zoom_in_threshold.reset()
        self._zoom_out_threshold.reset()
        self._gesture_buffer.clear()
        self._current_gesture = GestureMode.NEUTRAL
        self._pending_gesture = GestureMode.NEUTRAL
        self._pending_count = 0
        self.has_selection = False
