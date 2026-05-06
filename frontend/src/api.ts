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

// Active gesture set — display data only. Dispatch is server-driven via GET /dispatch.
export type GestureEntry = { key: string; label: string; description: string };

export const GESTURES: Record<string, GestureEntry> = {
  thumbs_up:   { key: "→",   label: "Next",    description: "Advance to the next slide" },
  thumbs_down: { key: "←",   label: "Back",    description: "Go back to the previous slide" },
  open_hand:   { key: "Esc", label: "Exit",    description: "Exit the presentation" },
  point_up:    { key: "F5",  label: "Start",   description: "Start presentation from beginning" },
  ok:          { key: "B",   label: "Blank",   description: "Blank / unblank the screen" },
};

// Kept for any legacy code still importing GESTURE_KEYS.
export const GESTURE_KEYS: Record<string, string> = Object.fromEntries(
  Object.entries(GESTURES).map(([g, e]) => [g, e.key])
);
