import os
import time
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

MODEL_PATH = os.path.join(os.path.dirname(__file__), "gesture_recognizer.task")
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"
)


def _ensure_model() -> None:
    if not os.path.exists(MODEL_PATH):
        print("Downloading gesture_recognizer.task …")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Download complete.")


# ---------------------------------------------------------------------------
# Hand skeleton connections (MediaPipe landmark index pairs)
# ---------------------------------------------------------------------------

_HAND_CONNECTIONS = [
    (0, 1),  (1, 2),  (2, 3),  (3, 4),           # thumb
    (0, 5),  (5, 6),  (6, 7),  (7, 8),            # index
    (5, 9),  (9, 10), (10, 11), (11, 12),          # middle
    (9, 13), (13, 14), (14, 15), (15, 16),         # ring
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),  # pinky
]

# Skin tone range in HSV. Hue 0-20 catches most skin tones; bump the upper
# hue to ~25 if detection is weak in warm lighting or for darker skin tones.
_SKIN_LOWER = np.array([0,  20,  70], dtype=np.uint8)
_SKIN_UPPER = np.array([20, 255, 255], dtype=np.uint8)

# Colours for the on-screen legend drawn bottom-left in _process.
_LEGEND = [
    ((0,   200,   0), "Skeleton"),   # green   - MediaPipe landmarks
    ((0,   140, 255), "Contour"),    # orange  - skin region boundary
    ((255,   0, 200), "Hull"),       # magenta - convex hull
    ((200, 200,   0), "Canny"),      # cyan    - skin edge detection
]

# ---------------------------------------------------------------------------
# Gesture label mapping
# ---------------------------------------------------------------------------
# MediaPipe GestureRecognizer returns category names from its trained model.
# We map them to the strings the frontend expects. ILoveYou is intentionally
# absent — returning None for unknown labels is the desired fallback.

_GESTURE_MAP: dict[str, str] = {
    "Thumb_Up":    "thumbs_up",
    "Thumb_Down":  "thumbs_down",
    "Victory":     "peace",
    "Closed_Fist": "fist",
    "Open_Palm":   "open_hand",
    "Pointing_Up": "point_up",
    "Ok":          "ok",
}


# ---------------------------------------------------------------------------
# HandRecognizer
# ---------------------------------------------------------------------------


class HandRecognizer:
    """
    Runs the webcam capture loop and processes each frame through the image
    processing pipeline. Results are stored for Flask to read.

    generate_frames() -- yields MJPEG bytes for /stream
    current_gesture() -- returns the latest gesture name, or None (thread-safe)
    """

    def __init__(self, camera_index: int = 0) -> None:
        _ensure_model()

        self._cap = cv2.VideoCapture(camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera {camera_index}")

        options = mp_vision.GestureRecognizerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        )
        self._detector = mp_vision.GestureRecognizer.create_from_options(options)

        # Built once here — creating these per frame adds measurable overhead.
        # clipLimit=2.0 stops CLAHE from over-amplifying noise in dark tiles.
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        # Ellipse fits a hand region better than a square kernel.
        self._morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

        # _loop writes here, public methods read — both go through the lock.
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
            time.sleep(1 / 30)  # cap stream output at ~30 fps

    def stop(self) -> None:
        self._running = False
        self._thread.join()
        self._cap.release()
        self._detector.close()

    # ------------------------------------------------------------------
    # Internal frame loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        """Camera loop — runs in a daemon thread, writes to _frame and _gesture."""
        while self._running:
            ok, frame = self._cap.read()
            if not ok:
                time.sleep(0.01)  # don't spin at 100% CPU if the camera drops
                continue

            frame = cv2.flip(frame, 1)  # mirror so left/right feel natural

            gesture = self._process(frame)

            _, jpeg = cv2.imencode(".jpg", frame)
            with self._lock:
                self._gesture = gesture
                self._frame = jpeg.tobytes()

    # ------------------------------------------------------------------
    # Core image processing pipeline
    # ------------------------------------------------------------------

    def _process(self, frame: np.ndarray) -> str | None:
        """
        Run the full CV pipeline on one frame.  Annotates the frame in-place
        and returns the recognised gesture string (or None).
        """
        h, w = frame.shape[:2]

        # CLAHE needs a single channel, so grayscale first. After applying it,
        # Gaussian blur knocks out sensor noise before MediaPipe runs — without
        # this step, detection noticeably degrades in dim or uneven lighting.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        enhanced = self._clahe.apply(gray)
        enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        preprocessed = cv2.GaussianBlur(enhanced_bgr, (5, 5), 0)

        # Feed the preprocessed frame into MediaPipe, not the raw one.
        rgb = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._detector.recognize(mp_image)

        # HSV thresholding for skin. The hue channel is less affected by shadows
        # and highlights than BGR, so the mask stays usable as lighting shifts.
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        skin_mask = cv2.inRange(hsv, _SKIN_LOWER, _SKIN_UPPER)

        # OPEN kills small blobs that slipped through the HSV threshold.
        # The extra dilate fills in gaps from specular highlights on knuckles,
        # which often drop below the skin saturation floor.
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, self._morph_kernel)
        skin_mask = cv2.dilate(skin_mask, self._morph_kernel, iterations=1)

        # RETR_EXTERNAL skips holes inside regions. Largest contour by area
        # is the hand; skip anything under 2000px as background noise.
        contours, _ = cv2.findContours(
            skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if contours:
            largest = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest) > 2000:
                cv2.drawContours(frame, [largest], -1, (0, 140, 255), 2)

                # Convex hull in magenta. The indentations where the hull pulls
                # away from the contour are the finger gaps (convexity defects),
                # which could feed a more sophisticated classifier later.
                hull = cv2.convexHull(largest)
                cv2.drawContours(frame, [hull], -1, (255, 0, 200), 2)

        # Canny on the skin region only — masking first means we're not
        # picking up every edge in the background. Thresholds 40/120 work
        # well for finger edges; raise the lower value if output is cluttered.
        skin_gray = cv2.bitwise_and(enhanced, enhanced, mask=skin_mask)
        edges = cv2.Canny(skin_gray, 40, 120)
        edge_overlay = np.zeros_like(frame)
        edge_overlay[edges > 0] = (200, 200, 0)  # cyan in BGR
        cv2.addWeighted(frame, 1.0, edge_overlay, 0.5, 0, frame)

        # Sobel gradient magnitude for the full frame, shrunk to a corner inset.
        # sx and sy are the X and Y partial derivatives; magnitude() combines them
        # into an edge-strength map regardless of edge direction.
        sx = cv2.Sobel(enhanced, cv2.CV_64F, 1, 0, ksize=3)  # dI/dx
        sy = cv2.Sobel(enhanced, cv2.CV_64F, 0, 1, ksize=3)  # dI/dy
        sobel_mag = cv2.convertScaleAbs(cv2.magnitude(sx, sy))

        iw, ih = w // 5, h // 5
        inset = cv2.resize(sobel_mag, (iw, ih))
        frame[0:ih, w - iw:w] = cv2.cvtColor(inset, cv2.COLOR_GRAY2BGR)
        cv2.rectangle(frame, (w - iw, 0), (w - 1, ih - 1), (180, 180, 180), 1)
        cv2.putText(frame, "Sobel", (w - iw + 4, 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)

        # Landmarks come as 0-1 fractions of the frame dimensions.
        gesture = None
        if result.hand_landmarks:
            lm = result.hand_landmarks[0]

            for a, b in _HAND_CONNECTIONS:
                x1, y1 = int(lm[a].x * w), int(lm[a].y * h)
                x2, y2 = int(lm[b].x * w), int(lm[b].y * h)
                cv2.line(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)

            for point in lm:
                cx, cy = int(point.x * w), int(point.y * h)
                cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)

            # GestureRecognizer returns one list per hand; [0][0] is the top result.
            if result.gestures:
                category = result.gestures[0][0].category_name
                gesture = _GESTURE_MAP.get(category)

            if gesture:
                cv2.putText(
                    frame, gesture, (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2, cv2.LINE_AA,
                )

        # Colour key, bottom-left corner.
        for i, (colour, label) in enumerate(_LEGEND):
            y_pos = h - 20 - i * 20
            cv2.circle(frame, (14, y_pos), 5, colour, -1)
            cv2.putText(frame, label, (24, y_pos + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, colour, 1)

        return gesture
