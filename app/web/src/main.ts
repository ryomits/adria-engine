// Display entry point (the app shell). Reads display.json, follows the
// harness signal files, and hands one frame per animation frame to the avatar.
//
// URL parameters (development / offline checks):
//   debug        show the current state and mouth value
//   checker      checkerboard background instead of transparency
//   still        deterministic frame: no blinking or motion, camera snapped
//   state=...    fixed conversation state (with "still")
//   expr=...     fixed expression name (with "still")
//   mouth=0..1   fixed mouth openness (with "still")
//   avatar=placeholder  show the placeholder character whatever display.json says
//   vrm=avatars/x.vrm  show another model than display.json names
import type { AvatarOptions, AvatarView } from "./avatar/AvatarView";
import { createPlaceholderAvatar } from "./avatar/placeholder/PlaceholderAvatar";
import { createVrmAvatar } from "./avatar/vrmAvatar/VrmAvatar";
import { parseDisplayConfig, type DisplayConfig } from "./config/parseDisplayConfig";
import { selectVrmPath } from "./config/selectVrmPath";
import { reportToNative } from "./native/reportToNative";
import { frameFromSignals, type AvatarFrame } from "./shell/frameFromSignals";
import { parseState, type ConversationState, type NowPlaying } from "./signals/parseSignals";
import { pollSignals } from "./signals/pollSignals";

const params = new URLSearchParams(location.search);
const still = params.has("still");
const debugEl = document.getElementById("debug");
if (params.has("checker")) document.body.classList.add("checker");
if (params.has("debug") && debugEl) debugEl.style.display = "block";

function stillFrame(): AvatarFrame {
  return {
    state: parseState({ state: params.get("state") }),
    expression: params.get("expr") ?? "neutral",
    mouth: Number(params.get("mouth") ?? 0),
  };
}

async function createAvatar(config: DisplayConfig, options: AvatarOptions): Promise<AvatarView> {
  const stage = document.getElementById("stage");
  if (!stage) throw new Error("index.html has no #stage element");
  if (params.get("avatar") === "placeholder" || config.avatar === "placeholder") {
    reportToNative("avatar: placeholder");
    return createPlaceholderAvatar(stage, options);
  }
  const vrmPath = selectVrmPath(config.vrm, params.get("vrm"));
  const avatar = await createVrmAvatar(stage, config, `home/${vrmPath}`, options);
  reportToNative(`avatar: loaded ${vrmPath}`);
  return avatar;
}

async function main(): Promise<void> {
  const res = await fetch("home/display.json", { cache: "no-store" });
  if (!res.ok) throw new Error(`display.json: HTTP ${res.status}`);
  const config = parseDisplayConfig(await res.json());

  const avatar = await createAvatar(config, { still });
  window.addEventListener("resize", () => avatar.resize(window.innerWidth, window.innerHeight));

  let state: ConversationState = "idle";
  let nowPlaying: NowPlaying | null = null;
  if (!still) {
    pollSignals((s) => {
      state = s.state;
      nowPlaying = s.nowPlaying;
    });
  }

  let last = performance.now();
  let frames = 0;
  const render = (now: number) => {
    const dt = still ? 0 : Math.min((now - last) / 1000, 0.1);
    last = now;
    const frame = still
      ? stillFrame()
      : frameFromSignals(state, nowPlaying, Date.now() / 1000, config.lipSync.fallbackHz);
    avatar.render(frame, dt);
    if (debugEl && params.has("debug")) {
      debugEl.textContent = `state: ${frame.state}\nexpr:  ${frame.expression}\nmouth: ${frame.mouth.toFixed(2)}`;
    }
    frames += 1;
    if (frames === 1) reportToNative(`first frame ${window.innerWidth}x${window.innerHeight}`);
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
