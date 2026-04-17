import os
from flask import Flask, Response, jsonify, send_from_directory
from flask_cors import CORS
from hand_recognizer import HandRecognizer

DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

app = Flask(__name__, static_folder=DIST, static_url_path="")
CORS(app)

recognizer = HandRecognizer()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/stream")
def stream():
    return Response(
        recognizer.generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@app.route("/gesture")
def gesture():
    return jsonify({"gesture": recognizer.current_gesture()})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5001, threaded=True)
    finally:
        recognizer.stop()
