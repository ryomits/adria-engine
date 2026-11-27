// How the character holds itself in each conversation state. The state is
// shown by the character alone: asleep in standby, attentive while listening,
// looking up while thinking, lively while speaking. Angles are radians on the
// normalized VRM bones (positive pitch = head forward / down).
import type { ExpressionWeights } from "../expressions/resolveExpression";
import type { ConversationState } from "../signals/parseSignals";

export type Pose = {
  headPitch: number;
  headYaw: number;
  headRoll: number;
  /** Upper-body lean (positive = forward). */
  spinePitch: number;
  /** 0 = eyes open, 1 = closed. */
  eyesClosed: number;
  /** Whether the eyes blink now and then (not while asleep). */
  blinks: boolean;
  /** Seconds per breath and how far the chest moves. */
  breathSec: number;
  breathDepth: number;
  /** Expression weights added to the expression of the line being spoken. */
  mood: ExpressionWeights;
};

const wave = (hz: number, t: number) => Math.sin(2 * Math.PI * hz * t);

export function statePose(state: ConversationState, t: number): Pose {
  switch (state) {
    case "idle":
      // Asleep: head drooping, swaying very slowly with deep breaths.
      return {
        headPitch: 0.28 + 0.03 * wave(1 / 6, t),
        headYaw: 0,
        headRoll: 0.12 + 0.02 * wave(1 / 9, t),
        spinePitch: 0.06,
        eyesClosed: 1,
        blinks: false,
        breathSec: 6,
        breathDepth: 0.035,
        mood: { relaxed: 0.6 },
      };
    case "listening":
      // Attentive: leaning in a little, small nods, a soft smile.
      return {
        headPitch: 0.06 * Math.max(0, wave(0.8, t)),
        headYaw: 0,
        headRoll: 0.06,
        spinePitch: 0.04,
        eyesClosed: 0,
        blinks: true,
        breathSec: 4,
        breathDepth: 0.015,
        mood: { happy: 0.3 },
      };
    case "thinking":
      // Looking up and aside, head tilted.
      return {
        headPitch: -0.14,
        headYaw: 0.16,
        headRoll: 0.16 + 0.02 * wave(0.3, t),
        spinePitch: 0,
        eyesClosed: 0,
        blinks: true,
        breathSec: 4,
        breathDepth: 0.015,
        mood: {},
      };
    case "speaking":
      return {
        headPitch: 0.02 * wave(0.7, t),
        headYaw: 0.04 * wave(0.3, t),
        headRoll: 0,
        spinePitch: 0,
        eyesClosed: 0,
        blinks: true,
        breathSec: 4,
        breathDepth: 0.015,
        mood: {},
      };
  }
}
