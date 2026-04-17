# CLAUDE.md — Gesture Recognition App

## Project Overview

A computer vision gesture recognition system with two parts, both living in this repo:

1. **Flask backend** (`server/`) — reads webcam frames, runs the ML hand recogniser, streams MJPEG video, and exposes a `/gesture` polling endpoint.
2. **React frontend** (`frontend/`) — displays the live stream and current gesture; serves as a read-only dashboard (no user configuration).

The final deliverable is a React app (TSX + Vite) compiled to static HTML/JS, served directly by Flask.

---

## Architecture

```
[Webcam]
   │
   ▼
[HandRecognizer (Python / OpenCV + ML)]
   │  recognised gesture string
   ▼
[Flask WebServer]  ──── GET /stream   (MJPEG)  ────►
                   ──── GET /gesture  (JSON)   ────►  [React UI]
                   ──── GET /         (static) ────►
```

Flask is the only backend. All frontend API calls go to `http://localhost:5001`
(or are proxied via Vite dev server in development).

---

## File Structure

```
project root/
├── server/
│   ├── app.py              ← Flask entry point
│   ├── hand_recognizer.py  ← OpenCV + ML gesture detection
│   └── requirements.txt
└── frontend/
    ├── CLAUDE.md           ← this file
    ├── PLAN.md
    ├── INTEGRATION.md
    ├── index.html
    ├── vite.config.ts
    ├── tsconfig.json
    ├── tsconfig.app.json
    ├── tsconfig.node.json
    ├── package.json
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── api.ts              ← all fetch() calls + GESTURE_KEYS map
        ├── vite-env.d.ts
        ├── components/
        │   ├── StreamPanel.tsx     ← live MJPEG feed + gesture label overlay
        │   ├── GestureLabel.tsx    ← polls GET /gesture, shows current gesture
        │   └── MappingLegend.tsx   ← read-only gesture → key reference table
        └── index.css
```

---

## Flask Server Spec (`server/`)

### `app.py`

Responsibilities:
- Serve the built React app at `GET /` from `../frontend/dist/`
- Expose `GET /stream` — MJPEG stream from the hand recogniser
- Expose `GET /gesture` — current recognised gesture as JSON
- Enable `flask-cors` for development convenience

```python
# skeleton — actual implementation in server/app.py
from flask import Flask, Response, jsonify, send_from_directory
from flask_cors import CORS
from hand_recognizer import HandRecognizer

app = Flask(__name__, static_folder="../frontend/dist", static_url_path="")
CORS(app)
recognizer = HandRecognizer()

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/stream")
def stream():
    return Response(
        recognizer.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/gesture")
def gesture():
    return jsonify({"gesture": recognizer.current_gesture()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
```

### `hand_recognizer.py`

Responsibilities:
- Open the webcam with `cv2.VideoCapture`
- Run gesture detection on each frame (ML model TBD)
- Annotate frames with gesture overlay
- Expose `generate_frames()` — yields MJPEG-encoded bytes
- Expose `current_gesture()` — returns the latest gesture string or `None`

MJPEG frame format (required by Flask `/stream`):
```
b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n"
```

### `requirements.txt`

```
flask
flask-cors
opencv-python
# add ML dependencies (e.g. mediapipe, torch) here
```

---

## Frontend API Endpoints

### `GET /stream`
- Returns a **MJPEG stream** (`multipart/x-mixed-replace; boundary=frame`)
- Consumed as `<img src="/stream" />` — do NOT use WebSockets or canvas

### `GET /gesture`
- Returns the current recognised gesture
- Response: `{ "gesture": "thumbs_up" }` or `{ "gesture": null }`
- Polled every **500ms** via `setInterval` in `GestureLabel`

---

## Frontend Component Specs

### `GestureLabel`
- Polls `GET /gesture` every 500ms via `fetchGesture()` from `api.ts`
- Displays gesture name + emoji when active (e.g. "👍 thumbs_up")
- Shows "—" when gesture is `null` or `"none"`
- Silent error handling — never crashes the UI on failed fetch
- Cleans up interval on unmount

```ts
useEffect(() => {
  const id = setInterval(async () => {
    try {
      const g = await fetchGesture();
      setGesture(g);
    } catch { /* ignore */ }
  }, 500);
  return () => clearInterval(id);
}, []);
```

### `StreamPanel`
- `<img src={STREAM_URL} />` — plain MJPEG, no canvas
- `onError` shows a "Stream unavailable" placeholder
- `GestureLabel` absolutely positioned over the stream (bottom-left)

### `MappingLegend`
- Read-only table: gesture name | key badge
- Data comes from `GESTURE_KEYS` in `api.ts` — no user interaction

---

## `api.ts`

```ts
const BASE = "";

export const STREAM_URL = `${BASE}/stream`;

export const fetchGesture = async (): Promise<string | null> => {
  const res = await fetch(`${BASE}/gesture`);
  const data = (await res.json()) as { gesture?: string };
  return data.gesture ?? null;
};

// Fixed gesture → key mappings. Update once gesture set is confirmed.
export const GESTURE_KEYS: Record<string, string> = {
  thumbs_up:   "ArrowRight",
  thumbs_down: "ArrowLeft",
  peace:       "ArrowUp",
  fist:        "ArrowDown",
  open_hand:   "Space",
  point_up:    "Enter",
  ok:          "Escape",
};
```

---

## Vite Config

```ts
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/gesture": "http://localhost:5001",
      "/stream":  "http://localhost:5001",
    },
  },
});
```

---

## Key Rules & Constraints

- **No user key configuration** — gesture→key mappings are fixed in `GESTURE_KEYS`
- **Static HTML output** — `vite build` only; no SSR, no Node runtime at deploy time
- **No WebSockets** — MJPEG over HTTP for stream, polling for gesture
- **No UI library** — plain React + CSS
- **Error resilience** — stream error → placeholder UI; gesture fetch error → silent fail

---

## Run Instructions

```bash
# Backend
cd server
pip install -r requirements.txt
python app.py          # runs on http://localhost:5001

# Frontend (dev)
cd frontend
npm install
npm run dev            # runs on http://localhost:5173, proxies to Flask

# Frontend (production build)
cd frontend
npm run build          # outputs to frontend/dist/
# Flask then serves dist/ automatically
```
