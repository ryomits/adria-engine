// Autonomous body motion: rest pose, breathing, idle glances and state gestures.
// Runs entirely on the display side; the harness only provides the state.
import type { VRM, VRMHumanBoneName } from "@pixiv/three-vrm";
import { approach } from "../framing/approach";
import type { ConversationState } from "../signals/parseSignals";

type Gesture = { headPitch: number; headYaw: number; headRoll: number };

const TAU = 0.35;

export class ProceduralMotion {
  private t = 0;
  private glance = { yaw: 0, pitch: 0 };
  private nextGlanceAt = 3;
  private head: Gesture = { headPitch: 0, headYaw: 0, headRoll: 0 };

  constructor(
    private readonly vrm: VRM,
    private readonly rand: () => number = Math.random,
  ) {
    this.applyRestPose();
  }

  private bone(name: VRMHumanBoneName) {
    return this.vrm.humanoid.getNormalizedBoneNode(name);
  }

  private applyRestPose(): void {
    // VRM rest pose is a T-pose; lower the arms to the sides.
    const l = this.bone("leftUpperArm");
    const r = this.bone("rightUpperArm");
    if (l) l.rotation.z = -1.25;
    if (r) r.rotation.z = 1.25;
    const ll = this.bone("leftLowerArm");
    const rl = this.bone("rightLowerArm");
    if (ll) ll.rotation.z = -0.12;
    if (rl) rl.rotation.z = 0.12;
  }

  update(dt: number, state: ConversationState): void {
    this.t += dt;
    const t = this.t;

    // Breathing: slow chest rise and shoulder lift (about 4 s per breath).
    const breath = Math.sin((2 * Math.PI * t) / 4);
    const chest = this.bone("chest");
    if (chest) chest.rotation.x = -0.015 * breath;
    const ls = this.bone("leftShoulder");
    const rs = this.bone("rightShoulder");
    if (ls) ls.rotation.z = 0.02 * breath;
    if (rs) rs.rotation.z = -0.02 * breath;

    // Occasional glances while idle.
    if (t >= this.nextGlanceAt) {
      this.glance = { yaw: (this.rand() - 0.5) * 0.3, pitch: (this.rand() - 0.5) * 0.1 };
      this.nextGlanceAt = t + 4 + 6 * this.rand();
    }

    const target = this.gestureFor(state, t);
    const k = { dt, tau: TAU };
    this.head = {
      headPitch: approach({ current: this.head.headPitch, target: target.headPitch, ...k }),
      headYaw: approach({ current: this.head.headYaw, target: target.headYaw, ...k }),
      headRoll: approach({ current: this.head.headRoll, target: target.headRoll, ...k }),
    };
    const neck = this.bone("neck");
    const head = this.bone("head");
    if (neck) neck.rotation.set(this.head.headPitch * 0.4, this.head.headYaw * 0.4, this.head.headRoll * 0.4);
    if (head) head.rotation.set(this.head.headPitch * 0.6, this.head.headYaw * 0.6, this.head.headRoll * 0.6);
  }

  private gestureFor(state: ConversationState, t: number): Gesture {
    switch (state) {
      case "listening":
        // Small nods, about one per second.
        return { headPitch: 0.07 * Math.max(0, Math.sin(2 * Math.PI * 1.0 * t)), headYaw: 0, headRoll: 0.04 };
      case "thinking":
        return { headPitch: -0.06, headYaw: 0.08, headRoll: 0.14 };
      case "speaking":
        return { headPitch: 0.02 * Math.sin(2 * Math.PI * 0.7 * t), headYaw: 0.04 * Math.sin(2 * Math.PI * 0.3 * t), headRoll: 0 };
      default:
        return { headPitch: this.glance.pitch, headYaw: this.glance.yaw, headRoll: 0 };
    }
  }
}
