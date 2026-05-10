import collections
import threading
import time

try:
    import pyautogui
    # Disable the failsafe corner so a hand near the screen edge
    # doesn't abort the process unexpectedly.
    pyautogui.FAILSAFE = False
    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    # pyautogui is optional — the app still works without it,
    # keystrokes just won't be sent to other applications.
    _PYAUTOGUI_AVAILABLE = False

# pyautogui key names (different from JS KeyboardEvent key names).
DEFAULT_BINDINGS: dict[str, str] = {
    "thumbs_up":   "right",   # next slide
    "thumbs_down": "left",    # previous slide
    "open_hand":   "esc",     # exit presentation
    "point_up":    "f5",      # start / enter full-screen
    "ok":          "b",       # blank / unblank screen
}

# Translation table from pyautogui key names to JS KeyboardEvent.key values.
# Only used for the frontend display — the OS keystroke goes through pyautogui.
_JS_KEY: dict[str, str] = {
    "right": "ArrowRight",
    "left":  "ArrowLeft",
    "esc":   "Escape",
    "f5":    "F5",
    "b":     "b",
}


class Operator:
    """
    Tracks gesture changes and fires OS-level keystrokes via pyautogui.

    The tracker thread polls HandRecognizer.current_gesture() every
    poll_interval seconds. When the gesture changes from the stored
    baseline, the key is pressed at the OS level (affects any focused app,
    including PowerPoint/Keynote) and also queued for the frontend to
    display via GET /dispatch.

    Baseline semantics: advances on every change including to None, so
    the same gesture re-fires after the hand disappears and reappears.
    """

    def __init__(self, recognizer, poll_interval: float = 0.05) -> None:
        self._recognizer = recognizer
        self._poll_interval = poll_interval

        self._lock = threading.Lock()
        self._bindings: dict[str, str] = dict(DEFAULT_BINDINGS)
        self._baseline: str | None = None
        # maxlen=10 so a burst of rapid gestures can't build up an unbounded backlog.
        self._queue: collections.deque[str] = collections.deque(maxlen=10)

        self._running = True
        self._thread = threading.Thread(target=self._tracker, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def bind(self, gesture: str, key: str) -> None:
        with self._lock:
            self._bindings[gesture] = key

    def get_bindings(self) -> dict[str, str]:
        with self._lock:
            return dict(self._bindings)

    def next_dispatch(self) -> str | None:
        """Pop the oldest pending JS key name for the frontend display."""
        with self._lock:
            return self._queue.popleft() if self._queue else None

    def stop(self) -> None:
        self._running = False
        self._thread.join()

    # ------------------------------------------------------------------
    # Internal tracker loop
    # ------------------------------------------------------------------

    def _tracker(self) -> None:
        while self._running:
            current = self._recognizer.current_gesture()
            with self._lock:
                if current != self._baseline:
                    if current is not None:
                        key = self._bindings.get(current)
                        if key:
                            self._press(key)
                            js_key = _JS_KEY.get(key, key)
                            self._queue.append(js_key)
                    self._baseline = current
            time.sleep(self._poll_interval)

    def _press(self, key: str) -> None:
        if _PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.press(key)
            except Exception:
                # Swallow any platform-level errors (e.g. no display on headless machines)
                # so they don't crash the tracker thread.
                pass
