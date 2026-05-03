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

---

## Full system architecture

Once your model is plugged in, the complete data flow looks like this:

```
[Webcam]
   │  OpenCV frames
   ▼
[HandRecognizer._loop()]          ← background thread
   │  MediaPipe: 21 landmarks
   ├─► classify_gesture(lm)       ← YOUR MODEL GOES HERE
   │       │
   │   gesture string or None
   │       │
   ├─► _gesture  (thread-safe)    ← read by Flask GET /gesture (display)
   └─► _frame   (JPEG bytes)      ← read by Flask GET /stream  (video)
          │
          ▼
[Operator._tracker()]             ← background thread, polls every 50 ms
   │  compares current gesture vs. _baseline
   │  on change: looks up key in _bindings, appends to _queue
   ▼
[Operator._queue]                 ← deque(maxlen=10), thread-safe
   │
   ▼
[Flask GET /dispatch]             ← React polls every 100 ms
   │  pops next key or returns null
   ▼
[React GestureLabel — Interval B]
   │  document.dispatchEvent(new KeyboardEvent("keydown", { key }))
   ▼
[Browser / target app receives key event]
```

**React also runs Interval A** (500 ms) that polls `GET /gesture` purely for
the visual label overlay. These two intervals are independent.

---

## Operator class (`gesture_operator.py`)

The `Operator` is a singleton (instantiated once in `app.py`) that decouples
gesture detection from keyboard dispatch. It adds two things the raw
`HandRecognizer` does not provide:

1. **Baseline tracking** — fires only on the *leading edge* of a gesture
   change, not on every frame where the gesture is held.
2. **Runtime-configurable bindings** — gesture→key pairs can be updated via
   `POST /bind` without restarting the server or redeploying the frontend.

### Baseline semantics

`_baseline` stores the last gesture that was processed (dispatched or skipped).
It advances on *every* gesture change, including to `None`.

- Hand disappears → `_baseline = None`. This is the **reset state**: the next
  time the same gesture appears it will fire again.
- Gesture changes while hand is visible → fires once for the new gesture, then
  no more until the gesture changes again or the hand disappears.

### Thread safety

A single `threading.Lock` guards `_bindings`, `_baseline`, and `_queue`.
`current_gesture()` (called from the tracker thread) uses HandRecognizer's own
lock internally — no deadlock risk since the two locks are independent and
neither is held while acquiring the other.

The deque has `maxlen=10`: if the frontend stops polling, old stale events
auto-expire rather than accumulating indefinitely.

### Public API

| Method | Description |
|--------|-------------|
| `bind(gesture, key)` | Update a gesture→key binding at runtime. Thread-safe. |
| `get_bindings()` | Return a snapshot of the current bindings dict. |
| `next_dispatch()` | Pop and return the oldest pending key, or `None`. Called by `GET /dispatch`. |
| `stop()` | Shut down the tracker thread cleanly. Called in `app.py`'s `finally` block. |

---

## POST /bind — update a gesture binding

Changes a gesture→key mapping at runtime. Changes are in-memory only and reset
on server restart.

**Request:**
```json
{ "gesture": "thumbs_up", "key": "ArrowRight" }
```

- `gesture` — one of the recognised gesture name strings (see output table above)
- `key` — a valid `KeyboardEvent.key` value (`"ArrowRight"`, `"Space"`, `"a"`, `"F5"`, …)

**Success response:**
```json
{ "ok": true }
```

**Validation error (400):**
```json
{ "ok": false, "error": "gesture and key required" }
```

**Example:**
```bash
curl -X POST http://localhost:5001/bind \
  -H "Content-Type: application/json" \
  -d '{"gesture": "thumbs_up", "key": "a"}'
```

After this call, showing a thumbs-up will fire `KeyboardEvent { key: "a" }`
instead of `ArrowRight` — no restart needed.

---

## GET /dispatch — consume the next pending key

Returns the oldest key that the Operator has enqueued since the last call, or
`null` if nothing is pending. **This is a destructive read** — each key is
returned exactly once.

**Response when a key is waiting:**
```json
{ "key": "ArrowRight" }
```

**Response when the queue is empty:**
```json
{ "key": null }
```

The React frontend polls this endpoint every **100 ms** and fires a synthetic
`KeyboardEvent` when `key` is non-null. You do not need to call this endpoint
yourself; it exists so the frontend can receive server-side dispatch events.

---

## Performance and latency

| Stage | Typical time |
|-------|-------------|
| Camera frame captured | ~33 ms (30 fps) |
| MediaPipe inference | ~5–15 ms (CPU) |
| Operator tracker poll | 50 ms |
| Frontend dispatch poll | 100 ms |
| **Worst-case gesture → keydown** | **~150 ms** |

The old client-side approach polled `GET /gesture` at 500 ms intervals, giving
a worst-case latency of ~500 ms. The server-side Operator + 100 ms dispatch
poll cuts this to ~150 ms.

---

## Server-side vs. client-side dispatch

**Old approach (before Operator):** `GestureLabel.tsx` polled `GET /gesture`
every 500 ms, compared consecutive results to detect the leading edge, and
fired a `KeyboardEvent` in JavaScript. Problems:

- 500 ms worst-case latency.
- If two different gestures occurred between polls, the second was silently
  missed.
- Gesture→key mapping was hardcoded in the frontend bundle; changing it
  required a frontend rebuild.

**New approach (Operator):** The tracker thread fires at 50 ms precision and
enqueues every leading-edge transition in a persistent in-process queue. React
drains the queue at 100 ms. Benefits:

- ~150 ms worst-case latency.
- No missed gestures (the deque buffers up to 10 pending events).
- Bindings are reconfigurable at runtime via `POST /bind`.
- The queue is inspectable for debugging (add a `GET /bindings` route if needed).

---

## What you should NOT change (updated)

| File / symbol | Reason |
|---------------|--------|
| `app.py` | Flask routes and server config — add to it if needed, don't rewrite |
| `HandRecognizer.__init__`, `_loop`, `_process` | Camera loop and MediaPipe pipeline |
| `generate_frames()` | MJPEG streaming logic |
| `current_gesture()` | Thread-safe getter consumed by Operator and Flask |
| `Operator._tracker` internals | Baseline logic is deliberately designed |
| `gesture_operator.py` thread/lock structure | Thread safety is non-trivial |
| `frontend/src/components/StreamPanel.tsx` | Stream display is complete |
| `frontend/src/components/MappingLegend.tsx` | Legend is display-only |
