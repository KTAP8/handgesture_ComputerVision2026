import collections
import threading
import time

DEFAULT_BINDINGS: dict[str, str] = {
    "thumbs_up":   "ArrowRight",
    "thumbs_down": "ArrowLeft",
    "peace":       "ArrowUp",
    "fist":        "ArrowDown",
    "open_hand":   "Space",
    "point_up":    "Enter",
    "ok":          "Escape",
}


class Operator:
    """
    Singleton that tracks gesture changes from a baseline and enqueues
    keyboard actions for the frontend to consume via GET /dispatch.

    The tracker thread polls HandRecognizer.current_gesture() every
    poll_interval seconds. When the gesture changes from the stored
    baseline, the dispatcher looks up the key binding and appends it
    to the dispatch queue.

    Baseline semantics:
    - Advances on every gesture change, including to None.
    - None is the "reset" state: it allows the same gesture to re-fire
      after the hand disappears and reappears.
    - maxlen=10 on the deque prevents unbounded growth if the frontend
      is slow or stopped.
    """

    def __init__(self, recognizer, poll_interval: float = 0.05) -> None:
        self._recognizer = recognizer
        self._poll_interval = poll_interval

        self._lock = threading.Lock()
        self._bindings: dict[str, str] = dict(DEFAULT_BINDINGS)
        self._baseline: str | None = None
        self._queue: collections.deque[str] = collections.deque(maxlen=10)

        self._running = True
        self._thread = threading.Thread(target=self._tracker, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def bind(self, gesture: str, key: str) -> None:
        """Update the gesture→key binding at runtime."""
        with self._lock:
            self._bindings[gesture] = key

    def get_bindings(self) -> dict[str, str]:
        """Return a snapshot of the current bindings."""
        with self._lock:
            return dict(self._bindings)

    def next_dispatch(self) -> str | None:
        """Pop and return the oldest pending key, or None if the queue is empty."""
        with self._lock:
            return self._queue.popleft() if self._queue else None

    def stop(self) -> None:
        self._running = False
        self._thread.join()

    # ------------------------------------------------------------------
    # Internal tracker loop (runs in daemon thread)
    # ------------------------------------------------------------------

    def _tracker(self) -> None:
        while self._running:
            current = self._recognizer.current_gesture()
            with self._lock:
                if current != self._baseline:
                    if current is not None:
                        key = self._bindings.get(current)
                        if key:
                            self._queue.append(key)
                    self._baseline = current
            time.sleep(self._poll_interval)
