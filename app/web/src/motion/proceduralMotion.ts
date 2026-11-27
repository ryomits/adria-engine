// Autonomous body motion: rest pose, breathing and the pose of each state
// (see statePose). Runs entirely on the display side; the harness only
// provides the state. Every value eases toward the pose of the current state,
// so falling asleep and waking up are gradual.
import type { VRM, VRMHumanBoneName } from "@pixiv/three-vrm";
import type { ExpressionWeights } from "../expressions/resolveExpression";
import { approach } from "../framing/approach";
import type { ConversationState } from "../signals/parseSignals";
import { statePose } from "./statePose";

const TAU = 0.35; // head and body
const EYES_TAU = 0.4; // eyes closing when falling asleep, opening when woken

export class ProceduralMotion {
  private t = 0;
  private breathPhase = 0;
  private head = { pitch: 0, yaw: 0, roll: 0 };
  private spine = 0;
  private breathDepth = 0.015;
  /** Eyelid closure from the state (0..1); blinking is added by the caller. */
  eyesClosed = 0;
  /** Whether the caller should blink now and then. */
  blinks = true;
  /** Expression weights for the state, eased. */
  readonly mood: ExpressionWeights = {};

  constructor(private readonly vrm: VRM) {
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

  /** Advance by `dt` seconds (0 snaps straight to the pose, for still frames). */
  update(dt: number, state: ConversationState): void {
    this.t += dt;
    const pose = statePose(state, this.t);
    const ease = (current: number, target: number, tau = TAU) =>
      dt === 0 ? target : approach({ current, target, dt, tau });

    this.head = {
      pitch: ease(this.head.pitch, pose.headPitch),
      yaw: ease(this.head.yaw, pose.headYaw),
      roll: ease(this.head.roll, pose.headRoll),
    };
    this.spine = ease(this.spine, pose.spinePitch);
    this.eyesClosed = ease(this.eyesClosed, pose.eyesClosed, EYES_TAU);
    this.blinks = pose.blinks;
    for (const name of new Set([...Object.keys(this.mood), ...Object.keys(pose.mood)])) {
      this.mood[name] = ease(this.mood[name] ?? 0, pose.mood[name] ?? 0);
    }

    // Breathing: the phase advances continuously, so changing the rate
    // (slower when asleep) never makes the chest jump.
    this.breathPhase += (2 * Math.PI * dt) / pose.breathSec;
    this.breathDepth = ease(this.breathDepth, pose.breathDepth);
    const breath = Math.sin(this.breathPhase) * this.breathDepth;

    const spine = this.bone("spine");
    if (spine) spine.rotation.x = this.spine;
    const chest = this.bone("chest");
    if (chest) chest.rotation.x = -breath;
    const ls = this.bone("leftShoulder");
    const rs = this.bone("rightShoulder");
    if (ls) ls.rotation.z = breath * 1.3;
    if (rs) rs.rotation.z = -breath * 1.3;
    const neck = this.bone("neck");
    const head = this.bone("head");
    const { pitch, yaw, roll } = this.head;
    if (neck) neck.rotation.set(pitch * 0.4, yaw * 0.4, roll * 0.4);
    if (head) head.rotation.set(pitch * 0.6, yaw * 0.6, roll * 0.6);
  }
}
