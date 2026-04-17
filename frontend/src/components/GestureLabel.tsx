import { useEffect, useRef, useState } from "react";
import { fetchGesture, GESTURE_KEYS } from "../api";

const GESTURE_EMOJI: Record<string, string> = {
  thumbs_up:   "👍",
  thumbs_down: "👎",
  peace:       "✌️",
  fist:        "✊",
  open_hand:   "🖐️",
  point_up:    "☝️",
  ok:          "👌",
};

export default function GestureLabel() {
  const [gesture, setGesture] = useState<string | null>(null);
  const prevGesture = useRef<string | null>(null);

  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const g = await fetchGesture();
        setGesture(g);

        // Dispatch a keydown event on leading edge (gesture first appears)
        const isNew = g && g !== "none" && g !== prevGesture.current;
        if (isNew) {
          const key = GESTURE_KEYS[g];
          if (key) {
            document.dispatchEvent(
              new KeyboardEvent("keydown", { key, bubbles: true })
            );
          }
        }

        prevGesture.current = g;
      } catch {
        // silently ignore fetch errors
      }
    }, 500);
    return () => clearInterval(id);
  }, []);

  const isEmpty = !gesture || gesture === "none";
  const emoji = gesture ? (GESTURE_EMOJI[gesture] ?? "🤚") : "";

  return (
    <div className="gesture-label" data-empty={isEmpty}>
      {isEmpty ? "—" : `${emoji} ${gesture}`}
    </div>
  );
}
