import { useEffect, useState } from "react";
import { fetchGesture } from "../api";

const GESTURE_EMOJI: Record<string, string> = {
  thumbs_up:   "👍",
  thumbs_down: "👎",
  open_hand:   "🖐️",
  point_up:    "☝️",
  ok:          "🤟",
};

export default function GestureReadout() {
  const [gesture, setGesture] = useState<string | null>(null);

  // Poll the server for the current gesture every 500ms.
  // Errors are swallowed so a dropped connection doesn't break the UI.
  useEffect(() => {
    const id = setInterval(async () => {
      try {
        setGesture(await fetchGesture());
      } catch {
        // silent
      }
    }, 500);
    return () => clearInterval(id);
  }, []);

  const active = !!gesture && gesture !== "none";
  const emoji = active ? (GESTURE_EMOJI[gesture!] ?? "🤚") : null;

  return (
    <div className="gesture-readout">
      <p className="section-label">Detected Gesture</p>
      <div className="readout-state" data-active={active}>
        {active ? (
          <>
            <span className="readout-emoji">{emoji}</span>
            <span className="readout-name">{gesture}</span>
          </>
        ) : (
          <span className="readout-name" data-empty="true">—</span>
        )}
      </div>
    </div>
  );
}
