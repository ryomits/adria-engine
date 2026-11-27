// The replaceable drawing layer. The app shell (signals, state badge, window)
// hands every frame to an AvatarView and knows nothing about how the
// character is drawn, so a new avatar is one more implementation of this
// interface and nothing else changes.
import type { AvatarFrame } from "../shell/frameFromSignals";

export interface AvatarView {
  /** Draw one frame. `dt` is the time since the previous frame, in seconds (0 for a still frame). */
  render(frame: AvatarFrame, dt: number): void;
  /** The window was resized (CSS pixels). */
  resize(width: number, height: number): void;
}

export type AvatarOptions = {
  /** Deterministic frame for offline checks: no blinking, idle motion or transitions. */
  still: boolean;
};
