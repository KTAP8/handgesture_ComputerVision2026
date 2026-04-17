import os
import threading
import urllib.request
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python  # type: ignore[import-untyped]
from mediapipe.tasks.python import vision as mp_vision  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# Model download
# ---------------------------------------------------------------------------

MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)

def _ensure_model() -> None:
    if not os.path.exists(MODEL_PATH):
        print("Downloading hand_landmarker.task …")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Download complete.")

# ---------------------------------------------------------------------------
# Hand connections for manual landmark drawing
# ---------------------------------------------------------------------------

_HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),          # thumb
    (0,5),(5,6),(6,7),(7,8),           # index
    (5,9),(9,10),(10,11),(11,12),      # middle
    (9,13),(13,14),(14,15),(15,16),    # ring
    (13,17),(0,17),(17,18),(18,19),(19,20),  # pinky
]

# ---------------------------------------------------------------------------
# Gesture classification
# ---------------------------------------------------------------------------
# Landmark indices (same as MediaPipe spec):
#   0  = wrist
#   4  = thumb tip,  3 = thumb IP,  2 = thumb MCP
#   8  = index tip,  7 = index DIP, 6 = index PIP, 5 = index MCP
#   12 = middle tip, 11 = middle DIP, 10 = middle PIP
#   16 = ring tip,   15 = ring DIP,   14 = ring PIP
#   20 = pinky tip,  19 = pinky DIP,  18 = pinky PIP

def _finger_extended(lm, tip: int, pip: int) -> bool:
    return lm[tip].y < lm[pip].y


def _thumb_extended(lm) -> bool:
    return abs(lm[4].x - lm[2].x) > 0.05


def classify_gesture(lm) -> str | None:
    """
    Map 21 hand landmarks to a gesture name string.
    Returns a key matching GESTURE_KEYS in the frontend, or None.

    TODO: Replace with your trained ML model's inference once ready.
          Landmark format: list of objects with .x .y .z (normalised 0-1).
    """
    index  = _finger_extended(lm, 8, 6)
    middle = _finger_extended(lm, 12, 10)
    ring   = _finger_extended(lm, 16, 14)
    pinky  = _finger_extended(lm, 20, 18)
    thumb  = _thumb_extended(lm)
    count  = sum([index, middle, ring, pinky])

    if count == 4:
        return "open_hand"

    if index and middle and not ring and not pinky:
        return "peace"

    if index and not middle and not ring and not pinky:
        return "point_up"

    if count == 0 and not thumb:
        return "fist"

    tip_dist = np.hypot(lm[4].x - lm[8].x, lm[4].y - lm[8].y)
    if tip_dist < 0.07 and middle and ring and pinky:
        return "ok"

    if thumb and count == 0:
        if lm[4].y < lm[0].y:
            return "thumbs_up"
        if lm[4].y > lm[0].y:
            return "thumbs_down"

    return None

# ---------------------------------------------------------------------------
# HandRecognizer
# ---------------------------------------------------------------------------

class HandRecognizer:
    """
    Captures webcam frames, runs MediaPipe HandLandmarker (Tasks API),
    classifies the gesture, and annotates the frame.

    Public API:
      generate_frames()  →  generator of MJPEG bytes for Flask /stream
      current_gesture()  →  latest gesture string or None
    """

    def __init__(self, camera_index: int = 0) -> None:
        _ensure_model()

        self._cap = cv2.VideoCapture(camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera {camera_index}")

        options = mp_vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        )
        self._detector = mp_vision.HandLandmarker.create_from_options(options)

        self._lock = threading.Lock()
        self._gesture: str | None = None
        self._frame: bytes | None = None

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def current_gesture(self) -> str | None:
        with self._lock:
            return self._gesture

    def generate_frames(self):
        """Yield MJPEG bytes for Flask's multipart streaming response."""
        import time
        while True:
            with self._lock:
                frame = self._frame
            if frame is None:
                time.sleep(0.05)
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + frame
                + b"\r\n"
            )

    def stop(self) -> None:
        self._running = False
        self._thread.join()
        self._cap.release()
        self._detector.close()

    # ------------------------------------------------------------------
    # Internal frame loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while self._running:
            ok, frame = self._cap.read()
            if not ok:
                continue
            gesture = self._process(frame)
            _, jpeg = cv2.imencode(".jpg", frame)
            with self._lock:
                self._gesture = gesture
                self._frame = jpeg.tobytes()

    def _process(self, frame: np.ndarray) -> str | None:
        """Run HandLandmarker on one frame, annotate it in-place, return gesture."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._detector.detect(mp_image)

        if not result.hand_landmarks:
            return None

        lm = result.hand_landmarks[0]
        h, w = frame.shape[:2]

        # Draw connections
        for a, b in _HAND_CONNECTIONS:
            x1, y1 = int(lm[a].x * w), int(lm[a].y * h)
            x2, y2 = int(lm[b].x * w), int(lm[b].y * h)
            cv2.line(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)

        # Draw landmark dots
        for point in lm:
            cx, cy = int(point.x * w), int(point.y * h)
            cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)

        gesture = classify_gesture(lm)

        if gesture:
            cv2.putText(
                frame, gesture, (10, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2, cv2.LINE_AA,
            )

        return gesture
