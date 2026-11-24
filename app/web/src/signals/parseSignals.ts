// Parsing of the signal files written by the harness (runtime/state, runtime/now_playing).
// They are external input, so every field is validated here.

export const STATES = ["idle", "listening", "thinking", "speaking"] as const;
export type ConversationState = (typeof STATES)[number];

export type MouthCurve = { fps: number; values: number[] };

export type NowPlaying = {
  id: string;
  expression: string;
  startedAt: number;
  duration: number;
  mouth: MouthCurve | null;
};

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function isConversationState(v: unknown): v is ConversationState {
  return typeof v === "string" && (STATES as readonly string[]).includes(v);
}

export function parseState(raw: unknown): ConversationState {
  if (!isRecord(raw) || !isConversationState(raw.state)) return "idle";
  return raw.state;
}

function parseMouth(raw: unknown): MouthCurve | null {
  if (!isRecord(raw) || typeof raw.fps !== "number" || !Array.isArray(raw.values)) return null;
  const values = raw.values;
  if (!values.every((v): v is number => typeof v === "number")) return null;
  return { fps: raw.fps, values };
}

export function parseNowPlaying(raw: unknown): NowPlaying | null {
  if (!isRecord(raw) || raw.playing !== true) return null;
  if (typeof raw.started_at !== "number") return null;
  return {
    id: typeof raw.id === "string" ? raw.id : "",
    expression: typeof raw.x_expression === "string" ? raw.x_expression : "neutral",
    startedAt: raw.started_at,
    duration: typeof raw.duration === "number" ? raw.duration : 0,
    mouth: parseMouth(raw.mouth),
  };
}
