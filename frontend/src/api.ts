const BASE = "";

export const STREAM_URL = `${BASE}/stream`;

export const fetchGesture = async (): Promise<string | null> => {
  const res = await fetch(`${BASE}/gesture`);
  const data = (await res.json()) as { gesture?: string };
  return data.gesture ?? null;
};

export const fetchDispatch = async (): Promise<string | null> => {
  const res = await fetch(`${BASE}/dispatch`);
  const data = (await res.json()) as { key?: string };
  return data.key ?? null;
};

export const bindGesture = async (gesture: string, key: string): Promise<void> => {
  await fetch(`${BASE}/bind`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ gesture, key }),
  });
};

// Display-only gesture → key reference (used by MappingLegend).
// Keyboard dispatch is now server-driven via GET /dispatch.
export const GESTURE_KEYS: Record<string, string> = {
  thumbs_up:   "ArrowRight",
  thumbs_down: "ArrowLeft",
  peace:       "ArrowUp",
  fist:        "ArrowDown",
  open_hand:   "Space",
  point_up:    "Enter",
  ok:          "Escape",
};
