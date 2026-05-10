import os
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
from hand_recognizer import HandRecognizer
from gesture_operator import Operator

# Serve the pre-built React app from here when running in production.
DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

app = Flask(__name__, static_folder=DIST, static_url_path="")
CORS(app)

# On macOS, Continuity Camera (iPhone) is often assigned index 0,
# pushing the built-in FaceTime camera to index 1.
# Override with: CAMERA_INDEX=1 python app.py
_camera_index = int(os.environ.get("CAMERA_INDEX", 0))
recognizer = HandRecognizer(camera_index=_camera_index)
operator = Operator(recognizer)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    # Hand off to React for all page navigation.
    return send_from_directory(app.static_folder, "index.html")


@app.route("/stream")
def stream():
    # MJPEG multipart stream — consumed as a plain <img> tag on the frontend.
    return Response(
        recognizer.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/gesture")
def gesture():
    # Returns the most recently detected gesture name, or null if none.
    return jsonify({"gesture": recognizer.current_gesture()})


@app.route("/dispatch")
def dispatch():
    # Pops the next pending keystroke from the operator queue.
    # Returns null when there's nothing new to act on.
    return jsonify({"key": operator.next_dispatch()})


@app.route("/bind", methods=["POST"])
def bind():
    # Lets the frontend remap a gesture to a different key at runtime.
    data = request.get_json(force=True)
    gesture_name = data.get("gesture", "")
    key = data.get("key", "")
    if not gesture_name or not key:
        return jsonify({"ok": False, "error": "gesture and key required"}), 400
    operator.bind(gesture_name, key)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5001, threaded=True)
    finally:
        # Make sure the camera and background threads are cleaned up on exit.
        recognizer.stop()
        operator.stop()
