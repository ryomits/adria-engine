import type { PerspectiveCamera } from "three";
import type { Framing } from "../config/parseDisplayConfig";
import { approach } from "./approach";

/** Moves the camera and the character smoothly toward the framing of the current state. */
export class CameraRig {
  private current: Framing;

  constructor(
    private readonly camera: PerspectiveCamera,
    initial: Framing,
    private readonly transitionSec: number,
  ) {
    this.current = { ...initial, target: [...initial.target] };
    this.apply();
  }

  /** Returns the horizontal offset to apply to the character. */
  update(dt: number, goal: Framing): number {
    const tau = this.transitionSec / 3;
    const step = (current: number, target: number) => approach({ current, target, dt, tau });
    const c = this.current;
    this.current = {
      target: [step(c.target[0], goal.target[0]), step(c.target[1], goal.target[1]), step(c.target[2], goal.target[2])],
      distance: step(c.distance, goal.distance),
      fov: step(c.fov, goal.fov),
      modelX: step(c.modelX, goal.modelX),
    };
    this.apply();
    return this.current.modelX;
  }

  snap(goal: Framing): number {
    this.current = { ...goal, target: [...goal.target] };
    this.apply();
    return goal.modelX;
  }

  private apply(): void {
    const [x, y, z] = this.current.target;
    this.camera.fov = this.current.fov;
    this.camera.position.set(x, y, z + this.current.distance);
    this.camera.lookAt(x, y, z);
    this.camera.updateProjectionMatrix();
  }
}
