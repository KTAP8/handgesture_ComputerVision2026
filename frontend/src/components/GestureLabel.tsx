import { useEffect, useState } from "react";
import { fetchGesture, fetchDispatch } from "../api";

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

  // Interval A: display — update the visual label every 500ms
  useEffect(() => {
    const id = setInterval(async () => {
      try {
        setGesture(await fetchGesture());
      } catch {
        // silently ignore fetch errors
      }
    }, 500);
    return () => clearInterval(id);
  }, []);

  // Interval B: dispatch — drain server-side key queue every 100ms
  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const key = await fetchDispatch();
        if (key) {
          document.dispatchEvent(
            new KeyboardEvent("keydown", { key, bubbles: true })
          );
        }
      } catch {
        // silently ignore fetch errors
      }
    }, 100);
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
