# PLAN.md — Gesture Recognition App Implementation Plan

## Current State

- `frontend/` is fully scaffolded and builds cleanly (`npm run build` passes)
- React components done: `StreamPanel`, `GestureLabel` (with keyboard dispatcher), `MappingLegend`
- `api.ts` has `fetchGesture()`, `STREAM_URL`, and placeholder `GESTURE_KEYS`
- `server/` scaffolded: `app.py`, `hand_recognizer.py`, `requirements.txt` written

---

## Goal

Deliver a working end-to-end system:
1. Flask backend streams annotated webcam MJPEG and serves the current gesture via JSON
2. React frontend displays the live stream and recognised gesture
3. Flask serves the built React app as static files in production

---

## Implementation Steps

### Phase 1 — Flask Server (`server/`)  ← DONE

#### 1a. Project setup
- [x] Created `server/` directory at the project root
- [x] Created `server/requirements.txt` with `flask`, `flask-cors`, `opencv-python`, `mediapipe`
- [x] Created `server/app.py` — Flask entry point

#### 1b. `app.py` routes
- [x] `GET /` — serves `../frontend/dist/index.html`
- [x] `GET /stream` — MJPEG stream from `HandRecognizer.generate_frames()`
- [x] `GET /gesture` — returns `{ "gesture": <string | null> }`
- [x] `flask-cors` enabled

#### 1c. `hand_recognizer.py`
- [x] Opens webcam with `cv2.VideoCapture(0)`
- [x] Background thread: capture → MediaPipe detect → classify → annotate → store
- [x] `generate_frames()` yields MJPEG bytes
- [x] `current_gesture()` returns latest gesture string or `None`
- [x] Thread-safe via `threading.Lock`

---

### Phase 2 — Connect & Confirm Gesture Names  ← TODO

- [ ] Run Flask + React dev server together and verify the stream renders
- [ ] Confirm the exact gesture name strings the ML model outputs match the placeholder set
- [ ] Update `GESTURE_KEYS` in `frontend/src/api.ts` with agreed final mappings
- [ ] Update `GESTURE_EMOJI` maps in `GestureLabel.tsx` and `MappingLegend.tsx` if names changed
- [ ] Swap `classify_gesture()` heuristics in `hand_recognizer.py` for the real ML model

---

### Phase 3 — Keyboard Dispatcher  ← DONE

- [x] `useRef` tracks previous gesture for leading-edge detection
- [x] On new gesture: looks up key in `GESTURE_KEYS`, dispatches `keydown` on `document`
- [x] Trigger behaviour: **leading edge** (fires once when gesture first appears)

---

### Phase 4 — Production Wiring  ← TODO

- [x] `npm run build` produces clean `dist/`
- [ ] Confirm Flask `send_from_directory` serves `dist/index.html` at `GET /` (needs live test)
- [ ] End-to-end test: gesture in front of camera → label updates → key fires in browser

---

## File Checklist

```
project root/
├── .gitignore
├── README.md
├── server/                         ← TODO
│   ├── app.py
│   ├── hand_recognizer.py
│   └── requirements.txt
└── frontend/                       ← done
    ├── CLAUDE.md
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
        ├── api.ts                  ← GESTURE_KEYS needs final values
        ├── vite-env.d.ts
        ├── components/
        │   ├── StreamPanel.tsx
        │   ├── GestureLabel.tsx    ← keyboard dispatcher still TODO
        │   └── MappingLegend.tsx
        └── index.css
```

---

## Open Questions

| # | Question | Default Assumption |
|---|----------|--------------------|
| 1 | Exact gesture name strings from ML model | Use 7-item placeholder list |
| 2 | Final gesture → key mappings | Placeholders in `GESTURE_KEYS` |
| 3 | Keyboard dispatch trigger (leading / held / trailing) | Leading edge |
| 4 | Which ML library for hand detection? | TBD (mediapipe / torch / custom) |
| 5 | Single webcam or multiple? | `cv2.VideoCapture(0)` |

---

## Non-Goals

- No user-configurable key bindings — mappings are fixed in code
- No WebSockets — MJPEG over HTTP + polling only
- No heavy UI library
- No SSR / Node runtime at deploy time
