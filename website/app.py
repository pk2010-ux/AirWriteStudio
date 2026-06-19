import os
import sys
import base64
import cv2
import numpy as np
from flask import Flask, request, jsonify, send_from_directory

# Add app directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker, HandLandmarkerOptions, RunningMode
)
from config import (
    MP_MAX_NUM_HANDS, MP_MIN_DETECTION_CONFIDENCE, MP_MIN_TRACKING_CONFIDENCE,
)
from tracking.gesture_detector import GestureDetector

app = Flask(__name__, static_folder='.', static_url_path='')

# ─── MediaPipe Hand Landmarker ────────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "hand_landmarker.task")

options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=RunningMode.IMAGE,
    num_hands=MP_MAX_NUM_HANDS,
    min_hand_detection_confidence=MP_MIN_DETECTION_CONFIDENCE,
    min_hand_presence_confidence=MP_MIN_DETECTION_CONFIDENCE,
    min_tracking_confidence=MP_MIN_TRACKING_CONFIDENCE,
)
landmarker = HandLandmarker.create_from_options(options)

# ─── Gesture Detector (uses your full Python logic) ──────────────────────────
gesture_detector = GestureDetector()


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')


@app.route('/app.js')
def serve_js():
    return send_from_directory('.', 'app.js')


@app.route('/api/process_frame', methods=['POST'])
def process_frame():
    try:
        data = request.json
        if not data or 'frame' not in data:
            return jsonify({"error": "No frame provided"}), 400

        # Extract base64 image data
        frame_data = data['frame']
        if ',' in frame_data:
            frame_data = frame_data.split(',')[1]

        # Decode base64 to numpy array
        img_bytes = base64.b64decode(frame_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Failed to decode image"}), 400

        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Detect hands
        result = landmarker.detect(mp_image)

        response = {
            "hand_detected": False,
            "landmarks": None,
            "gesture": "neutral",
            "action_point": None
        }

        if result.hand_landmarks and len(result.hand_landmarks) > 0:
            response["hand_detected"] = True
            landmarks_list = result.hand_landmarks[0]

            # Extract raw landmarks for the frontend
            landmarks = [{"x": lm.x, "y": lm.y, "z": lm.z} for lm in landmarks_list]
            response["landmarks"] = landmarks

            # Run the FULL Python gesture detector
            gesture_mode, action_point = gesture_detector.detect(landmarks_list)
            response["gesture"] = gesture_mode.value  # "pen", "eraser", "select", "drag", "zoom_in", "zoom_out", "neutral"
            response["action_point"] = {"x": action_point[0], "y": action_point[1]}
        else:
            # Reset gesture detector when hand is lost
            gesture_detector.reset()

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)
