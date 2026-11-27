// What the character should show at a moment, from the harness signals.
// This is all an avatar renderer gets; it never reads the signal files itself.
import { fallbackMouth, sampleMouth } from "../lipsync/sampleMouth";
import type { ConversationState, NowPlaying } from "../signals/parseSignals";

export type AvatarFrame = {
  state: ConversationState;
  /** Expression name of the line being spoken ("neutral" otherwise). */
  expression: string;
  /** Mouth openness, 0..1. */
  mouth: number;
};

export function frameFromSignals(
  state: ConversationState,
  nowPlaying: NowPlaying | null,
  nowSec: number,
  fallbackHz: number,
): AvatarFrame {
  if (!nowPlaying) return { state, expression: "neutral", mouth: 0 };
  const elapsed = nowSec - nowPlaying.startedAt;
  const mouth = nowPlaying.mouth
    ? sampleMouth(nowPlaying.mouth, elapsed)
    : elapsed < nowPlaying.duration
      ? fallbackMouth(elapsed, fallbackHz)
      : 0;
  return { state, expression: nowPlaying.expression, mouth };
}
