import { useEffect, useState } from "react";
import { fetchGesture, fetchDispatch } from "../api";

const GESTURE_EMOJI: Record<string, string> = {
  thumbs_up:   "👍",
  thumbs_down: "👎",
  open_hand:   "🖐️",
  point_up:    "☝️",
  ok:          "🤟",
};

export default function GestureLabel() {
  const [gesture, setGesture] = useState<string | null>(null);

  // Update the displayed gesture label every 500ms. This doesn't need to be
  // faster because it's purely visual — the user can't perceive sub-500ms changes.
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

  // Drain the server's keystroke queue at 100ms so gestures feel responsive.
  // We re-fire the key as a DOM event so any focused element (e.g. a presentation
  // tool running in another window) can react to it via pyautogui on the server side.
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
