import { GESTURE_KEYS } from "../api";

const GESTURE_EMOJI: Record<string, string> = {
  thumbs_up:   "👍",
  thumbs_down: "👎",
  peace:       "✌️",
  fist:        "✊",
  open_hand:   "🖐️",
  point_up:    "☝️",
  ok:          "👌",
};

export default function MappingLegend() {
  return (
    <div className="mapping-legend">
      <p className="section-label">Key Map</p>
      <table className="mapping-table">
        <tbody>
          {Object.entries(GESTURE_KEYS).map(([gesture, key]) => (
            <tr key={gesture}>
              <td className="gesture-name">
                <span className="gesture-name-emoji">{GESTURE_EMOJI[gesture] ?? "🤚"}</span>
                {gesture}
              </td>
              <td>
                <span className="key-badge">{key}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
