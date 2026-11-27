// Appearance of the placeholder character per conversation state. Motion is
// small and slow on purpose (a calm character for a small child).
import type { ConversationState } from "../../signals/parseSignals";

export type Look = {
  /** Body color. */
  color: string;
  /** Vertical offset as a fraction of the body size (positive = up). */
  bob: number;
  /** Cycles per second of the bobbing. */
  hz: number;
  /** Eye openness, 0..1. */
  eyeOpen: number;
  /** Gaze offset as a fraction of the eye spacing (negative y = up). */
  gazeX: number;
  gazeY: number;
  /** Strength of the listening ring, 0..1. */
  ring: number;
  /** Number of thinking dots shown (0..3). */
  dots: number;
};

type Style = Omit<Look, "bob" | "dots"> & { amplitude: number };

const STYLES: Record<ConversationState, Style> = {
  idle: { color: "#B8C2D0", amplitude: 0.012, hz: 0.25, eyeOpen: 0.35, gazeX: 0, gazeY: 0.15, ring: 0 },
  listening: { color: "#8ED1AE", amplitude: 0.015, hz: 0.5, eyeOpen: 1, gazeX: 0, gazeY: 0, ring: 1 },
  thinking: { color: "#F3CD7A", amplitude: 0.01, hz: 0.35, eyeOpen: 0.85, gazeX: 0.25, gazeY: -0.3, ring: 0 },
  speaking: { color: "#F3A593", amplitude: 0.02, hz: 0.8, eyeOpen: 0.95, gazeX: 0, gazeY: 0, ring: 0 },
};

export function placeholderLook(state: ConversationState, t: number): Look {
  const { amplitude, ...style } = STYLES[state];
  return {
    ...style,
    bob: amplitude * Math.sin(2 * Math.PI * style.hz * t),
    dots: state === "thinking" ? 1 + (Math.floor(t * 1.5) % 3) : 0,
  };
}
