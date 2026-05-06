import { GESTURES } from "../api";

const GESTURE_EMOJI: Record<string, string> = {
  thumbs_up:   "👍",
  thumbs_down: "👎",
  open_hand:   "🖐️",
  point_up:    "☝️",
  ok:          "🤟",
};

export default function MappingLegend() {
  return (
    <div className="mapping-legend">
      <p className="section-label">Gesture Controls</p>
      <div className="mapping-list">
        {Object.entries(GESTURES).map(([gesture, { key, label, description }]) => (
          <div key={gesture} className="mapping-row">
            <span className="mapping-emoji">{GESTURE_EMOJI[gesture] ?? "🤚"}</span>
            <div className="mapping-info">
              <div className="mapping-top">
                <span className="mapping-label">{label}</span>
                <span className="key-badge">{key}</span>
              </div>
              <span className="mapping-desc">{description}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
