// Simple round character drawn on a 2D canvas, used until the real avatar
// exists. Its look per state comes from `placeholderLook`.
import { approach } from "../../framing/approach";
import { blinkWeight, nextBlinkInterval } from "../../motion/blink";
import type { AvatarFrame } from "../../shell/frameFromSignals";
import type { AvatarOptions, AvatarView } from "../AvatarView";
import { placeholderLook, type Look } from "./look";

type Rgb = [number, number, number];

function parseHex(hex: string): Rgb {
  const n = Number.parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function rgba([r, g, b]: Rgb, alpha = 1): string {
  return `rgba(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)}, ${alpha})`;
}

function shade([r, g, b]: Rgb, amount: number): Rgb {
  const mix = (c: number) => c + (amount > 0 ? (255 - c) * amount : c * amount);
  return [mix(r), mix(g), mix(b)];
}

const INK = "#3B3A4A";
const TRANSITION_TAU = 0.25; // seconds; color and gaze ease between states

export function createPlaceholderAvatar(parent: HTMLElement, options: AvatarOptions): AvatarView {
  const canvas = document.createElement("canvas");
  parent.appendChild(canvas);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("2D canvas is not available");
  let width = 0;
  let height = 0;
  const resize = (w: number, h: number) => {
    width = w;
    height = h;
    canvas.width = Math.round(w * devicePixelRatio);
    canvas.height = Math.round(h * devicePixelRatio);
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;
  };
  resize(parent.clientWidth, parent.clientHeight);

  let t = 0;
  let blinkAt = nextBlinkInterval(Math.random());
  let color: Rgb | null = null;
  let gaze = { x: 0, y: 0 };
  let eyeOpen = 1;

  const ease = (current: number, target: number, dt: number) =>
    options.still ? target : approach({ current, target, dt, tau: TRANSITION_TAU });

  return {
    resize,
    render(frame: AvatarFrame, dt: number) {
      t += dt;
      const look: Look = placeholderLook(frame.state, options.still ? 0 : t);
      const goal = parseHex(look.color);
      const prev = color ?? goal;
      color = [ease(prev[0], goal[0], dt), ease(prev[1], goal[1], dt), ease(prev[2], goal[2], dt)];
      gaze = { x: ease(gaze.x, look.gazeX, dt), y: ease(gaze.y, look.gazeY, dt) };
      eyeOpen = ease(eyeOpen, look.eyeOpen, dt);
      let blink = 0;
      if (!options.still) {
        if (t > blinkAt + 0.2) blinkAt = t + nextBlinkInterval(Math.random());
        blink = blinkWeight(t - blinkAt);
      }
      draw(ctx, { width, height, look, color, gaze, eyeOpen: eyeOpen * (1 - blink), mouth: frame.mouth, t });
    },
  };
}

type Scene = {
  width: number;
  height: number;
  look: Look;
  color: Rgb;
  gaze: { x: number; y: number };
  eyeOpen: number;
  mouth: number;
  t: number;
};

function draw(ctx: CanvasRenderingContext2D, s: Scene): void {
  const { width, height, look, color } = s;
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  ctx.clearRect(0, 0, width, height);
  const r = Math.min(width, height * 0.8) * 0.34;
  const cx = width / 2;
  const cy = height * 0.56 - look.bob * r * 4;

  // Listening ring: a soft halo that breathes slowly.
  if (look.ring > 0) {
    const pulse = 0.5 + 0.5 * Math.sin(2 * Math.PI * 0.5 * s.t);
    ctx.beginPath();
    ctx.arc(cx, cy, r * (1.16 + 0.04 * pulse), 0, 2 * Math.PI);
    ctx.lineWidth = r * 0.06;
    ctx.strokeStyle = rgba(color, 0.35 + 0.25 * pulse);
    ctx.stroke();
  }

  // Body.
  const body = ctx.createRadialGradient(cx - r * 0.3, cy - r * 0.35, r * 0.1, cx, cy, r);
  body.addColorStop(0, rgba(shade(color, 0.45)));
  body.addColorStop(1, rgba(color));
  ctx.beginPath();
  ctx.ellipse(cx, cy, r, r * 0.94, 0, 0, 2 * Math.PI);
  ctx.fillStyle = body;
  ctx.fill();

  // Cheeks.
  ctx.fillStyle = "rgba(240, 120, 120, 0.25)";
  for (const side of [-1, 1]) {
    ctx.beginPath();
    ctx.ellipse(cx + side * r * 0.52, cy + r * 0.12, r * 0.12, r * 0.07, 0, 0, 2 * Math.PI);
    ctx.fill();
  }

  // Eyes (they follow the gaze; a nearly closed eye is drawn as a line).
  ctx.fillStyle = INK;
  ctx.strokeStyle = INK;
  ctx.lineCap = "round";
  ctx.lineWidth = r * 0.04;
  for (const side of [-1, 1]) {
    const ex = cx + side * r * 0.32 + s.gaze.x * r * 0.4;
    const ey = cy - r * 0.12 + s.gaze.y * r * 0.4;
    const ry = r * 0.13 * s.eyeOpen;
    ctx.beginPath();
    if (ry < r * 0.02) {
      ctx.moveTo(ex - r * 0.08, ey);
      ctx.lineTo(ex + r * 0.08, ey);
      ctx.stroke();
    } else {
      ctx.ellipse(ex, ey, r * 0.08, ry, 0, 0, 2 * Math.PI);
      ctx.fill();
    }
  }

  // Mouth: a small smile, opening with the voice.
  const my = cy + r * 0.3;
  ctx.beginPath();
  if (s.mouth > 0.05) {
    ctx.ellipse(cx, my, r * 0.12, r * 0.2 * s.mouth, 0, 0, 2 * Math.PI);
    ctx.fill();
  } else {
    ctx.arc(cx, my - r * 0.08, r * 0.12, 0.2 * Math.PI, 0.8 * Math.PI);
    ctx.stroke();
  }

  // Thinking dots above the head.
  ctx.fillStyle = rgba(shade(color, -0.25));
  for (let i = 0; i < look.dots; i++) {
    ctx.beginPath();
    ctx.arc(cx + r * (0.55 + i * 0.22), cy - r * (1.05 + i * 0.12), r * (0.05 + i * 0.02), 0, 2 * Math.PI);
    ctx.fill();
  }
}
