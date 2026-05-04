# INTEGRATION.md

This file has two audiences:

- **[For me (frontend)](#for-me--frontend)** — what I still need to change once the ML model is plugged in
- **[For the team (backend / ML)](#for-the-team--backend--ml)** — the exact contract my code expects so you know what to implement

---

## For me — Frontend

### 1. Update `GESTURE_KEYS` once the gesture set is confirmed

**File:** `frontend/src/api.ts`

The current mappings are placeholders. Once the team agrees on which gestures map to which keys, replace the values:

```ts
export const GESTURE_KEYS: Record<string, string> = {
  thumbs_up:   "ArrowRight",   // ← placeholder
  thumbs_down: "ArrowLeft",    // ← placeholder
  peace:       "ArrowUp",      // ← placeholder
  fist:        "ArrowDown",    // ← placeholder
  open_hand:   "Space",        // ← placeholder
  point_up:    "Enter",        // ← placeholder
  ok:          "Escape",       // ← placeholder
};
```

Key strings must match the `KeyboardEvent.key` spec (e.g. `"ArrowRight"`, `"Space"`, `"a"`, `"F5"`).

---

### 2. Update gesture name strings if the ML model uses different names

**Files to update if names change:**
- `frontend/src/api.ts` — `GESTURE_KEYS` object keys
- `frontend/src/components/GestureLabel.tsx` — `GESTURE_EMOJI` map
- `frontend/src/components/MappingLegend.tsx` — `GESTURE_EMOJI` map

Current expected names (must match exactly, case-sensitive):
`thumbs_up`, `thumbs_down`, `peace`, `fist`, `open_hand`, `point_up`, `ok`

If the ML model outputs different casing or naming (e.g. `"ThumbsUp"`, `"PEACE"`), either:
- Update the keys in the three files above to match, **or**
- Add a normalisation step inside `fetchGesture()` in `api.ts`

Also add any new gestures the ML model introduces to the `GESTURE_EMOJI` map in both `GestureLabel.tsx` and `MappingLegend.tsx`.

---

### 3. Swap the placeholder gesture classifier for the real ML model

**File:** `server/hand_recognizer.py` — `classify_gesture()`

The current `classify_gesture()` is a geometric heuristic (finger up/down rules). Once the ML model is ready, replace this function's body with the real inference call. The function signature must stay the same:

```python
def classify_gesture(landmarks) -> str | None:
    # TODO: replace heuristics with model.predict(landmarks)
    ...
```

The `landmarks` argument is a MediaPipe `NormalizedLandmarkList` (list of 21 points with `.x`, `.y`, `.z`). If the model takes a different input format (e.g. a flat numpy array), add the conversion inside this function before calling the model.

---

### 4. Verify end-to-end in dev

1. `cd server && python app.py`
2. `cd frontend && npm run dev`
3. Open `http://localhost:5173`
4. Check: stream renders, gesture label updates, correct key fires in browser console (`window.addEventListener('keydown', e => console.log(e.key))`)

---

### 5. Production build before demo

```bash
cd frontend && npm run build   # outputs to frontend/dist/
python server/app.py           # Flask serves dist/ at GET /
```

---

### My checklist before demo

- [ ] `GESTURE_KEYS` updated with final agreed mappings
- [ ] Gesture name strings verified against ML model output
- [ ] `classify_gesture()` replaced with real ML model
- [ ] Stream renders live in browser
- [ ] Keyboard events fire correctly in end-to-end test
- [ ] `npm run build` passes cleanly
- [ ] Flask serves `dist/index.html` at `GET /`

---
---

## For the team — Backend / ML

> This section tells you exactly what my frontend and Flask server expect from
> the ML model and OpenCV pipeline so you can integrate without breaking anything.

---

### What I need from you

#### 1. A `classify_gesture()` function (or equivalent)

**Where it plugs in:** `server/hand_recognizer.py`

I already have the full webcam loop, MediaPipe landmark detection, MJPEG streaming, and Flask routes wired up. The only thing missing is the actual gesture classification.

**Current stub:**
```python
def classify_gesture(landmarks) -> str | None:
    # geometric heuristics — replace with your model
```

**Input:** `landmarks` is a MediaPipe `NormalizedLandmarkList` — a sequence of 21 landmark objects, each with `.x`, `.y`, `.z` (all normalised 0–1 relative to the frame).

**Output:** One of the agreed gesture name strings (see table below), or `None` / `"none"` when no gesture is recognised.

If your model takes a different input format, let me know and I'll add a conversion layer inside `classify_gesture()`.

---

#### 2. Agreed gesture name strings

The names your model outputs **must exactly match** what I have in the frontend. Current list:

| Name | Placeholder key |
|---|---|
| `thumbs_up` | `ArrowRight` |
| `thumbs_down` | `ArrowLeft` |
| `peace` | `ArrowUp` |
| `fist` | `ArrowDown` |
| `open_hand` | `Space` |
| `point_up` | `Enter` |
| `ok` | `Escape` |

If you add, remove, or rename gestures, tell me so I can update `GESTURE_KEYS`, `GESTURE_EMOJI`, and the legend.

---

#### 3. `GET /gesture` response contract

My Flask route already returns:

```python
@app.route("/gesture")
def gesture():
    return jsonify({"gesture": recognizer.current_gesture()})
```

The frontend polls this every **500ms** and expects:

```json
{ "gesture": "thumbs_up" }
```

When nothing is detected:

```json
{ "gesture": null }
```

Do not change the key name (`"gesture"`), the casing, or the nesting — the frontend will silently show nothing if the shape is wrong.

---

#### 4. `GET /stream` — MJPEG format

My `generate_frames()` already handles the MJPEG encoding. As long as `classify_gesture()` returns the right strings, you don't need to touch the streaming code.

If you want to change how frames are annotated (e.g. draw bounding boxes, confidence scores), edit `_process()` in `hand_recognizer.py` — that's where `cv2.putText` and `draw_landmarks` live.

---

#### 5. Installing your ML dependencies

Add any additional packages (e.g. `torch`, `torchvision`, a custom model package) to:

```
server/requirements.txt
```

The file currently has:
```
flask
flask-cors
opencv-python
mediapipe
```

---

#### 6. How to run the full stack

```bash
# Backend
cd server
pip install -r requirements.txt
python app.py          # webcam opens, Flask starts on http://localhost:5001

# Frontend (dev mode)
cd frontend
npm install
npm run dev            # http://localhost:5173, proxied to Flask
```
