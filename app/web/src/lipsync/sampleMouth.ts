import type { MouthCurve } from "../signals/parseSignals";

/** Mouth openness (0..1) at ``elapsed`` seconds into the line, from the harness curve. */
export function sampleMouth(curve: MouthCurve, elapsed: number): number {
  const pos = elapsed * curve.fps;
  if (pos < 0 || pos >= curve.values.length - 1) return 0;
  const i = Math.floor(pos);
  const frac = pos - i;
  return curve.values[i] * (1 - frac) + curve.values[i + 1] * frac;
}

/** Used when a line has no mouth curve: open and close at a steady rate. */
export function fallbackMouth(elapsed: number, hz: number): number {
  return 0.3 * (1 - Math.cos(2 * Math.PI * hz * elapsed));
}
