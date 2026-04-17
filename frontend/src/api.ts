const BASE = "";

export const STREAM_URL = `${BASE}/stream`;

export const fetchGesture = async (): Promise<string | null> => {
  const res = await fetch(`${BASE}/gesture`);
  const data = (await res.json()) as { gesture?: string };
  return data.gesture ?? null;
};

// Fixed gesture → key mappings.
// TODO: confirm exact keys with backend/team once gesture set is finalised.
export const GESTURE_KEYS: Record<string, string> = {
  thumbs_up:   "ArrowRight",
  thumbs_down: "ArrowLeft",
  peace:       "ArrowUp",
  fist:        "ArrowDown",
  open_hand:   "Space",
  point_up:    "Enter",
  ok:          "Escape",
};
