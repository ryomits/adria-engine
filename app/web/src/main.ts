// Display entry point. Loads the VRM named in display.json and drives it from
// the harness signal files.
//
// URL parameters (development / offline checks):
//   debug        show the current state and mouth value
//   checker      checkerboard background instead of transparency
//   still        deterministic frame: no blinking or motion, camera snapped
//   state=...    fixed conversation state (with "still")
//   expr=...     fixed expression name (with "still")
//   mouth=0..1   fixed mouth openness (with "still")
//   vrm=avatars/x.vrm  show another model than display.json names
import * as THREE from "three";
import { loadAvatar } from "./avatar/loadAvatar";
import { parseDisplayConfig } from "./config/parseDisplayConfig";
import { selectVrmPath } from "./config/selectVrmPath";
import { resolveExpression, type ExpressionWeights } from "./expressions/resolveExpression";
import { approach } from "./framing/approach";
import { CameraRig } from "./framing/cameraRig";
import { fallbackMouth, sampleMouth } from "./lipsync/sampleMouth";
import { blinkWeight, nextBlinkInterval } from "./motion/blink";
import { reportToNative } from "./native/reportToNative";
import { ProceduralMotion } from "./motion/proceduralMotion";
import { parseState, type ConversationState, type NowPlaying } from "./signals/parseSignals";
import { pollSignals } from "./signals/pollSignals";

const params = new URLSearchParams(location.search);
const still = params.has("still");
const debugEl = document.getElementById("debug");
if (params.has("checker")) document.body.classList.add("checker");
if (params.has("debug") && debugEl) debugEl.style.display = "block";

async function main(): Promise<void> {
  const res = await fetch("home/display.json", { cache: "no-store" });
  if (!res.ok) throw new Error(`display.json: HTTP ${res.status}`);
  const config = parseDisplayConfig(await res.json());

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, preserveDrawingBuffer: still });
  renderer.setClearColor(0x000000, 0);
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  document.body.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const light = new THREE.DirectionalLight(0xffffff, Math.PI);
  light.position.set(1, 1.5, 2);
  scene.add(light, new THREE.AmbientLight(0xffffff, 0.6));

  const camera = new THREE.PerspectiveCamera(30, window.innerWidth / window.innerHeight, 0.1, 20);
  window.addEventListener("resize", () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  const vrmPath = selectVrmPath(config.vrm, params.get("vrm"));
  const vrm = await loadAvatar(`home/${vrmPath}`);
  scene.add(vrm.scene);
  reportToNative(`loaded ${vrmPath}`);
  const motion = new ProceduralMotion(vrm);
  const rig = new CameraRig(camera, config.framing.idle, config.transitionSec);

  let state: ConversationState = still ? parseState({ state: params.get("state") }) : "idle";
  let nowPlaying: NowPlaying | null = null;
  if (!still) {
    pollSignals((s) => {
      state = s.state;
      nowPlaying = s.nowPlaying;
    });
  }

  // Every expression the table can touch is driven each frame, so moving to
  // neutral fades the previous expression out.
  const moodNames = new Set(Object.values(config.expressions).flatMap((w) => Object.keys(w)));
  const mood: ExpressionWeights = Object.fromEntries([...moodNames].map((n) => [n, 0]));
  let blinkAt = nextBlinkInterval(Math.random());
  let clockSec = 0;
  const clock = new THREE.Clock();
  let frames = 0;

  const render = () => {
    const dt = Math.min(clock.getDelta(), 0.1);
    clockSec += dt;
    const em = vrm.expressionManager;

    // Expression of the line being spoken (neutral otherwise).
    const exprName = still ? (params.get("expr") ?? "neutral") : (nowPlaying?.expression ?? "neutral");
    const goal = resolveExpression(config.expressions, exprName);
    for (const name of moodNames) {
      mood[name] = still ? (goal[name] ?? 0) : approach({ current: mood[name], target: goal[name] ?? 0, dt, tau: 0.15 });
      em?.setValue(name, mood[name]);
    }

    // Lip sync from the harness curve; open/close fallback without a curve.
    let mouth = 0;
    if (still) {
      mouth = Number(params.get("mouth") ?? 0);
    } else if (nowPlaying) {
      const elapsed = Date.now() / 1000 - nowPlaying.startedAt;
      mouth = nowPlaying.mouth
        ? sampleMouth(nowPlaying.mouth, elapsed)
        : elapsed < nowPlaying.duration ? fallbackMouth(elapsed, config.lipSync.fallbackHz) : 0;
    }
    em?.setValue(config.lipSync.expression, mouth);

    // Blinking.
    if (!still) {
      if (clockSec > blinkAt + 0.2) blinkAt = clockSec + nextBlinkInterval(Math.random());
      em?.setValue("blink", blinkWeight(clockSec - blinkAt));
    }

    if (!still) motion.update(dt, state);
    const goalFraming = config.framing[state];
    vrm.scene.position.x = still ? rig.snap(goalFraming) : rig.update(dt, goalFraming);
    vrm.update(still ? 0 : dt);
    renderer.render(scene, camera);

    if (debugEl && params.has("debug")) {
      debugEl.textContent = `state: ${state}\nexpr:  ${exprName}\nmouth: ${mouth.toFixed(2)}`;
    }
    frames += 1;
    if (frames === 1) {
      reportToNative(`first frame ${renderer.domElement.width}x${renderer.domElement.height}`);
    }
    if (still && frames === 3) document.title = "rendered";
    requestAnimationFrame(render);
  };
  requestAnimationFrame(render);
}

main().catch((err: unknown) => {
  console.error(err);
  reportToNative(`error: ${err instanceof Error ? err.message : String(err)}`);
  if (debugEl) {
    debugEl.style.display = "block";
    debugEl.textContent = `error: ${err instanceof Error ? err.message : String(err)}`;
  }
});
