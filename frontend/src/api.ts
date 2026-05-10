// Empty string means all requests go to the same origin.
// Vite proxies /gesture, /stream, /dispatch, and /bind to Flask in dev mode.
const BASE = "";

export const STREAM_URL = `${BASE}/stream`;

// Returns the gesture the server is currently seeing, or null if none detected.
export const fetchGesture = async (): Promise<string | null> => {
  const res = await fetch(`${BASE}/gesture`);
  const data = (await res.json()) as { gesture?: string };
  return data.gesture ?? null;
};

// Pops the next pending keystroke from the server's dispatch queue.
// Returns null when there's nothing new — callers should check before acting.
export const fetchDispatch = async (): Promise<string | null> => {
  const res = await fetch(`${BASE}/dispatch`);
  const data = (await res.json()) as { key?: string };
  return data.key ?? null;
};

// Overrides the key bound to a gesture on the server at runtime.
export const bindGesture = async (gesture: string, key: string): Promise<void> => {
  await fetch(`${BASE}/bind`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ gesture, key }),
  });
};

// Display data for each gesture — what key it maps to and a short description.
// The actual keystrokes are fired server-side; this is used for the UI only.
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
