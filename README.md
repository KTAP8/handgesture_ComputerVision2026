# Hand Gesture Control — CV 2026

A real-time hand gesture recognition system that translates webcam gestures into keyboard actions. Built with MediaPipe, Flask, and React.

---

## What It Does

The system reads your webcam, recognises hand gestures using MediaPipe, and presses the corresponding key at the OS level — so it works with any focused application, including PowerPoint and Keynote.

A live dashboard runs in the browser showing the camera feed, the currently detected gesture, and the gesture reference table.

---

## Gesture Reference

| Gesture | Key Sent | Action |
|---------|----------|--------|
| 👍 Thumbs up | → | Next slide |
| 👎 Thumbs down | ← | Previous slide |
| 🖐️ Open hand | Esc | Exit presentation |
| ☝️ Point up | F5 | Start presentation from beginning |
| 🤟 ILoveYou | B | Blank / unblank screen |

---

## Requirements

- Python 3.10 or later
- Node.js 18 or later
- A webcam

---

## Setup

### 1. Backend

```bash
cd server
pip install -r requirements.txt
```

The MediaPipe model (`gesture_recognizer.task`) is downloaded automatically on first run.

### 2. Frontend

```bash
cd frontend
npm install
```

---

## Running the App

### Development mode (live-reload UI)

Open two terminals:

**Terminal 1 — Flask server:**
```bash
cd server
python app.py
```

**Terminal 2 — Vite dev server:**
```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

### Production mode (single server)

```bash
cd frontend
npm run build

cd ../server
python app.py
```

Open `http://localhost:5001` in your browser. Flask serves the built frontend directly.

---

## macOS: Webcam Selection

On macOS, **Continuity Camera** (iPhone as webcam) is assigned camera index 0, which pushes the built-in FaceTime camera to index 1. If the wrong camera is used, set the index manually:

```bash
CAMERA_INDEX=1 python app.py
```

To find the right index, increment the number (0, 1, 2, …) until the correct camera appears in the dashboard.

---

## macOS: Accessibility Permission (Required for Key Dispatch)

For gestures to control other apps (PowerPoint, Keynote, etc.) the terminal running Flask needs Accessibility access:

1. Open **System Settings → Privacy & Security → Accessibility**
2. Click **+** and add your terminal app (Terminal.app or iTerm2)
3. Make sure the toggle is **on**

Without this permission, the gesture overlay in the browser still works, but no keystrokes will be sent to other applications.

---

## Demo: Controlling a Presentation

1. Open your `.pptx` or `.key` file
2. Start the Flask server: `python app.py`
3. Click into PowerPoint / Keynote to give it focus
4. Show gestures in front of the webcam:
   - 👍 Thumbs up — advance to the next slide
   - 👎 Thumbs down — go back
   - ☝️ Point up — start the slideshow (F5)
   - 🖐️ Open hand — exit the slideshow
   - 🤟 ILoveYou — blank the screen (press again to unblank)

The browser dashboard (`http://localhost:5001`) can stay open in the background — it shows which gesture is being detected in real time.

---

## Troubleshooting

**Gesture flickers or drops intermittently**
Make sure the hand is well-lit and fully visible. The system uses MediaPipe's VIDEO tracking mode so brief occlusion should recover quickly. If detection is still unstable, try improving lighting.

**No key is sent to PowerPoint**
Check the Accessibility permission (see above). Flask prints a startup message — confirm it says `Running on http://0.0.0.0:5001`.

**Stream shows "unavailable"**
Flask is not running, or it crashed on startup. Check the terminal for errors. The most common cause is the camera already being in use by another app (FaceTime, Zoom, etc.).

**Wrong camera is used**
Set `CAMERA_INDEX=1` (or 2, 3, …) as described in the webcam section above.

**`gesture_recognizer.task` download fails**
Download the model manually and place it in `server/`:
```
https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task
```

---

## Project Structure

```
├── server/
│   ├── app.py                  Flask server + API routes
│   ├── hand_recognizer.py      Webcam capture + MediaPipe pipeline
│   ├── gesture_operator.py     Gesture → keystroke dispatcher
│   ├── requirements.txt
│   └── FOR_AI_ENGINEERS.md     Guide for extending the ML pipeline
└── frontend/
    ├── src/
    │   ├── App.tsx
    │   ├── api.ts              Gesture definitions + fetch helpers
    │   └── components/
    │       ├── StreamPanel.tsx     Live camera feed
    │       ├── GestureReadout.tsx  Current gesture display
    │       ├── GestureLabel.tsx    On-video overlay + key dispatch
    │       └── MappingLegend.tsx   Gesture reference table
    └── INTEGRATION.md          Frontend ↔ backend contract
```
