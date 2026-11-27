// VRM model rendered with three.js: expressions, lip sync, blinking,
// procedural motion and per-state camera framing.
import * as THREE from "three";
import type { DisplayConfig } from "../../config/parseDisplayConfig";
import { resolveExpression, type ExpressionWeights } from "../../expressions/resolveExpression";
import { approach } from "../../framing/approach";
import { CameraRig } from "../../framing/cameraRig";
import { blinkWeight, nextBlinkInterval } from "../../motion/blink";
import { ProceduralMotion } from "../../motion/proceduralMotion";
import type { AvatarFrame } from "../../shell/frameFromSignals";
import type { AvatarOptions, AvatarView } from "../AvatarView";
import { loadAvatar } from "./loadAvatar";

export async function createVrmAvatar(
  parent: HTMLElement,
  config: DisplayConfig,
  url: string,
  options: AvatarOptions,
): Promise<AvatarView> {
  const renderer = new THREE.WebGLRenderer({
    alpha: true,
    antialias: true,
    preserveDrawingBuffer: options.still,
  });
  renderer.setClearColor(0x000000, 0);
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(parent.clientWidth, parent.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  parent.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const light = new THREE.DirectionalLight(0xffffff, Math.PI);
  light.position.set(1, 1.5, 2);
  scene.add(light, new THREE.AmbientLight(0xffffff, 0.6));
  const camera = new THREE.PerspectiveCamera(30, parent.clientWidth / parent.clientHeight, 0.1, 20);

  const vrm = await loadAvatar(url);
  scene.add(vrm.scene);
  const motion = new ProceduralMotion(vrm);
  const rig = new CameraRig(camera, config.framing.idle, config.transitionSec);

  // Every expression the table can touch is driven each frame, so moving to
  // neutral fades the previous expression out.
  const moodNames = new Set(Object.values(config.expressions).flatMap((w) => Object.keys(w)));
  const mood: ExpressionWeights = Object.fromEntries([...moodNames].map((n) => [n, 0]));
  let clockSec = 0;
  let blinkAt = nextBlinkInterval(Math.random());

  return {
    resize(width, height) {
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    },
    render(frame: AvatarFrame, dt: number) {
      const still = options.still;
      clockSec += dt;
      // The state is shown by the body: asleep in standby, attentive while
      // listening, and so on (eased inside ProceduralMotion).
      motion.update(dt, frame.state);
      const em = vrm.expressionManager;
      // Expression of the line being spoken, combined with the mood of the state.
      const goal = resolveExpression(config.expressions, frame.expression);
      for (const name of moodNames) {
        mood[name] = still
          ? (goal[name] ?? 0)
          : approach({ current: mood[name], target: goal[name] ?? 0, dt, tau: 0.15 });
      }
      for (const name of new Set([...moodNames, ...Object.keys(motion.mood)])) {
        em?.setValue(name, Math.max(mood[name] ?? 0, motion.mood[name] ?? 0));
      }
      em?.setValue(config.lipSync.expression, frame.mouth);
      // Eyes: closed while asleep, otherwise open with an occasional blink.
      let blink = 0;
      if (!still && motion.blinks) {
        if (clockSec > blinkAt + 0.2) blinkAt = clockSec + nextBlinkInterval(Math.random());
        blink = blinkWeight(clockSec - blinkAt);
      }
      em?.setValue("blink", Math.max(motion.eyesClosed, blink));
      const framing = config.framing[frame.state];
      vrm.scene.position.x = still ? rig.snap(framing) : rig.update(dt, framing);
      vrm.update(dt);
      renderer.render(scene, camera);
    },
  };
}
