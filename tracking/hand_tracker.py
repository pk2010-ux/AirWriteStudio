"""
AirWrite Studio - Hand Tracker
================================
Camera capture and MediaPipe HandLandmarker processing in a background QThread.
Uses the new MediaPipe Tasks API (v0.10.35+).
Emits signals for camera frames, hand landmarks, detection status, and FPS.
"""

import os
import time
import logging
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker, HandLandmarkerOptions, HandLandmarkerResult,
    HandLandmarksConnections, RunningMode,
    drawing_utils,
)
from mediapipe.tasks.python.vision.drawing_utils import DrawingSpec
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from config import (
    CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT,
    MP_MAX_NUM_HANDS, MP_MIN_DETECTION_CONFIDENCE, MP_MIN_TRACKING_CONFIDENCE,
)
from utils import qimage_from_cv, get_resource_path


# Path to the hand landmarker model file
MODEL_PATH = get_resource_path(os.path.join("assets", "hand_landmarker.task"))


class HandTracker(QThread):
    """
    Background thread that captures webcam frames, runs MediaPipe HandLandmarker
    detection, and emits results via Qt signals.
    
    Uses the new MediaPipe Tasks API with VIDEO running mode.
    
    Signals:
        frame_ready(QImage): Camera frame with landmark overlay for preview
        landmarks_ready(object): Hand landmarks as list[NormalizedLandmark] (or None)
        hand_detected(bool): Whether a hand is currently visible
        fps_updated(float): Current processing FPS (updated every 10 frames)
    """

    frame_ready = pyqtSignal(QImage)
    landmarks_ready = pyqtSignal(object)
    hand_detected = pyqtSignal(bool)
    fps_updated = pyqtSignal(float)
    error_occurred = pyqtSignal(str)

    def __init__(self, camera_index: int = CAMERA_INDEX, parent=None):
        super().__init__(parent)
        self._camera_index = camera_index
        self._running = False

        # Drawing specs for landmark visualization
        self._landmark_spec = DrawingSpec(
            color=(0, 255, 200), thickness=1, circle_radius=2
        )
        self._connection_spec = DrawingSpec(
            color=(0, 200, 160), thickness=1
        )

    def run(self):
        """Main capture loop. Runs until stop() is called."""
        self._running = True
        cap = None
        landmarker = None

        try:
            if not os.path.exists(MODEL_PATH):
                raise FileNotFoundError(f"MediaPipe model not found: {MODEL_PATH}")

            logging.info("Starting hand tracker with model: %s", MODEL_PATH)

            # Initialize HandLandmarker with VIDEO mode
            options = HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=MODEL_PATH),
                running_mode=RunningMode.VIDEO,
                num_hands=MP_MAX_NUM_HANDS,
                min_hand_detection_confidence=MP_MIN_DETECTION_CONFIDENCE,
                min_hand_presence_confidence=MP_MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=MP_MIN_TRACKING_CONFIDENCE,
            )
            landmarker = HandLandmarker.create_from_options(options)

            # Open camera. CAP_DSHOW avoids some Windows Media Foundation crashes
            # and long startup delays in frozen OpenCV applications.
            cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

            if not cap.isOpened():
                raise RuntimeError(
                    f"Could not open camera index {self._camera_index}. "
                    "Close other camera apps and check Windows camera permissions."
                )

            # FPS tracking
            frame_count = 0
            fps_start_time = time.time()
            last_hand_detected = False
            timestamp_ms = 0

            while self._running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue

                # Mirror the frame for natural interaction
                frame = cv2.flip(frame, 1)

                # Convert BGR to RGB for MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Create MediaPipe Image and detect
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                timestamp_ms += 33  # ~30fps increment
                result = landmarker.detect_for_video(mp_image, timestamp_ms)

                # Check for hand detection
                detected = (result.hand_landmarks is not None
                            and len(result.hand_landmarks) > 0)

                # Emit hand detection status only on change
                if detected != last_hand_detected:
                    self.hand_detected.emit(detected)
                    last_hand_detected = detected

                # Emit landmarks
                if detected:
                    # result.hand_landmarks[0] is list[NormalizedLandmark]
                    self.landmarks_ready.emit(result.hand_landmarks[0])

                    # Draw landmarks on the frame for preview
                    drawing_utils.draw_landmarks(
                        frame,
                        result.hand_landmarks[0],
                        HandLandmarksConnections.HAND_CONNECTIONS,
                        self._landmark_spec,
                        self._connection_spec,
                    )
                else:
                    self.landmarks_ready.emit(None)

                # Convert frame to QImage and emit for preview
                qt_image = qimage_from_cv(frame)
                self.frame_ready.emit(qt_image)

                # FPS calculation (update every 10 frames)
                frame_count += 1
                if frame_count % 10 == 0:
                    elapsed = time.time() - fps_start_time
                    if elapsed > 0:
                        fps = frame_count / elapsed
                        self.fps_updated.emit(fps)
                    frame_count = 0
                    fps_start_time = time.time()

        except Exception as exc:
            logging.exception("Hand tracker failed")
            self.error_occurred.emit(str(exc))
        finally:
            # Clean up resources
            self._running = False
            if cap is not None:
                cap.release()
            if landmarker is not None:
                landmarker.close()

    def stop(self):
        """Signal the thread to stop and wait for it to finish."""
        self._running = False
        self.wait(3000)  # Wait up to 3 seconds

    def set_camera(self, index: int):
        """
        Switch to a different camera. Requires restart.
        
        Args:
            index: Camera device index
        """
        was_running = self._running
        if was_running:
            self.stop()
        self._camera_index = index
        if was_running:
            self.start()

    @property
    def is_running(self) -> bool:
        """Whether the tracker is currently capturing."""
        return self._running
