import os
import sys
import base64
import cv2
import numpy as np
from flask import Flask, request, jsonify

# Add parent directory to path so we can import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    HandLandmarker, HandLandmarkerOptions, RunningMode
)
from config import MP_MAX_NUM_HANDS, MP_MIN_DETECTION_CONFIDENCE, MP_MIN_TRACKING_CONFIDENCE
from utils import get_resource_path

app = Flask(__name__)

# Initialize HandLandmarker in IMAGE mode for serverless stateless execution
MODEL_PATH = get_resource_path(os.path.join("assets", "hand_landmarker.task"))
options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=RunningMode.IMAGE,
    num_hands=MP_MAX_NUM_HANDS,
    min_hand_detection_confidence=MP_MIN_DETECTION_CONFIDENCE,
    min_hand_presence_confidence=MP_MIN_DETECTION_CONFIDENCE,
)
landmarker = HandLandmarker.create_from_options(options)

@app.route('/api/process_frame', methods=['POST'])
def process_frame():
    try:
        data = request.json
        if not data or 'frame' not in data:
            return jsonify({"error": "No frame provided"}), 400

        # Extract base64 image data (data:image/png;base64,...)
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
            "landmarks": None
        }

        if result.hand_landmarks and len(result.hand_landmarks) > 0:
            response["hand_detected"] = True
            # Extract landmarks for the first hand
            landmarks = [{"x": lm.x, "y": lm.y, "z": lm.z} for lm in result.hand_landmarks[0]]
            response["landmarks"] = landmarks

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Expose the app object for Vercel
# Vercel looks for the 'app' variable in api/index.py
