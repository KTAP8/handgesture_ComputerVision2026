# FOR_AI_ENGINEERS.md

This file is for the AI/ML team. The webcam pipeline, MJPEG streaming, Flask
server, and frontend are already built and running. Your job is to plug in the
trained gesture classification model. This document tells you exactly where and
how to do that.

---

## What is already done

- Flask server (`app.py`) — running on port 5001, serves the stream and gesture endpoints
- MediaPipe HandLandmarker — already integrated, detects 21 hand landmarks per frame from the webcam
- Gesture classifier stub (`classify_gesture()` in `hand_recognizer.py`) — currently uses geometric heuristics as a placeholder
- React frontend — polls `/gesture` every 500ms and displays the result live

**You only need to replace one function.**

---

## The one function you need to replace

**File:** `server/hand_recognizer.py`
**Function:** `classify_gesture(lm)`

```python
def classify_gesture(lm) -> str | None:
    """
    Map 21 hand landmarks to a gesture name string.
    Returns a key matching GESTURE_KEYS in the frontend, or None.

    TODO: Replace with your trained ML model's inference once ready.
          Landmark format: list of objects with .x .y .z (normalised 0-1).
    """
    # ... geometric heuristics (placeholder) ...
```

Replace the body of this function with your model's inference. Everything else
(camera loop, MJPEG encoding, Flask routes, frontend) stays untouched.

---

## Input format

`lm` is a list of **21 landmark objects** from MediaPipe HandLandmarker.
Each object has three attributes:

| Attribute | Type | Range | Description |
|-----------|------|-------|-------------|
| `.x` | float | 0.0 – 1.0 | Horizontal position (0 = left edge) |
| `.y` | float | 0.0 – 1.0 | Vertical position (0 = top edge) |
| `.z` | float | ~−0.1 – 0.1 | Depth relative to wrist (negative = closer) |

Landmark indices:
```
0  = wrist
1–4  = thumb  (MCP → tip)
5–8  = index  (MCP → tip)
9–12 = middle (MCP → tip)
13–16 = ring  (MCP → tip)
17–20 = pinky (MCP → tip)
```

If your model expects a flat numpy array, convert it inside `classify_gesture()`:

```python
import numpy as np

def classify_gesture(lm) -> str | None:
    features = np.array([[p.x, p.y, p.z] for p in lm], dtype=np.float32).flatten()
    # features.shape == (63,)
    ...
```

---

## Output format

Return one of these exact strings, or `None` if no gesture is recognised:

| String | Gesture |
|--------|---------|
| `"thumbs_up"` | 👍 |
| `"thumbs_down"` | 👎 |
| `"peace"` | ✌️ |
| `"fist"` | ✊ |
| `"open_hand"` | 🖐️ |
| `"point_up"` | ☝️ |
| `"ok"` | 👌 |

**Case and spelling matter.** The frontend matches these strings exactly.
Return `None` (not `""` or `"none"`) when no gesture is detected.

If your model recognises different gestures or uses different names, tell the
frontend developer so they can update the mapping.

---

## Example replacement

```python
import numpy as np
# import your_model  ← add your import here

def classify_gesture(lm) -> str | None:
    features = np.array([[p.x, p.y, p.z] for p in lm], dtype=np.float32).flatten()
    label = your_model.predict(features)   # returns a string or class index
    return label if label != "none" else None
```

If your model returns a class index instead of a string:

```python
LABEL_MAP = {
    0: "thumbs_up",
    1: "thumbs_down",
    2: "peace",
    3: "fist",
    4: "open_hand",
    5: "point_up",
    6: "ok",
}

def classify_gesture(lm) -> str | None:
    features = np.array([[p.x, p.y, p.z] for p in lm], dtype=np.float32).flatten()
    idx = your_model.predict(features)
    return LABEL_MAP.get(idx)
```

---

## Adding your model's dependencies

Add any extra packages to `server/requirements.txt`. Current contents:

```
flask
flask-cors
opencv-python
mediapipe
```

Example additions:
```
torch
scikit-learn
joblib
```

Then run `pip install -r requirements.txt`.

---

## How to test your integration

1. Install dependencies:
   ```bash
   cd server
   pip install -r requirements.txt
   ```

2. Start the server:
   ```bash
   python app.py
   ```

3. Check the gesture endpoint directly in a browser or terminal:
   ```bash
   curl http://localhost:5001/gesture
   # Expected: {"gesture": "thumbs_up"} or {"gesture": null}
   ```

4. Open the full UI (start frontend separately):
   ```bash
   cd frontend && npm run dev
   # Open http://localhost:5173
   ```

5. Show your hand to the webcam — the label on the stream should update
   within ~500ms.

---

## What you should NOT change

| File | Reason |
|------|--------|
| `app.py` | Flask routes and server config are wired up |
| `HandRecognizer.__init__`, `_loop`, `_process` | Camera loop and MediaPipe pipeline |
| `generate_frames()` | MJPEG streaming logic |
| `current_gesture()` | Thread-safe getter used by Flask |
| Anything in `frontend/` | Frontend is complete |

The only file you should edit is `hand_recognizer.py`, and the only part
you need to change is the body of `classify_gesture()`.
