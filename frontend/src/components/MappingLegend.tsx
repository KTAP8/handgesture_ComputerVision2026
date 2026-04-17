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
      <h2>Gesture Map</h2>
      <table className="mapping-table">
        <thead>
          <tr>
            <th>Gesture</th>
            <th>Key</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(GESTURE_KEYS).map(([gesture, key]) => (
            <tr key={gesture}>
              <td className="gesture-name">
                {GESTURE_EMOJI[gesture] ?? "🤚"} {gesture}
              </td>
              <td>
                <kbd className="key-badge">{key}</kbd>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
