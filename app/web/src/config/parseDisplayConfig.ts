// Validation of ADRIA_HOME/display.json (personal settings; external input).
import type { ExpressionTable } from "../expressions/resolveExpression";
import type { ConversationState } from "../signals/parseSignals";

export type Framing = {
  /** Point the camera looks at, in metres (x, y, z). */
  target: [number, number, number];
  distance: number;
  fov: number;
  /** Horizontal shift of the character, in metres (positive = right). */
  modelX: number;
};

/** Which renderer draws the character. Both follow the same frames. */
type AvatarChoice =
  | { avatar: "placeholder" }
  | {
      avatar: "vrm";
      /** VRM file under ADRIA_HOME. */
      vrm: string;
    };

export type DisplayConfig = AvatarChoice & {
  expressions: ExpressionTable;
  lipSync: { expression: string; fallbackHz: number };
  framing: Record<ConversationState, Framing>;
  transitionSec: number;
};

const DEFAULT_FRAMING: Record<ConversationState, Framing> = {
  // Upper body: the closed eyes and drooping head of the sleeping character must be visible.
  idle: { target: [0, 1.2, 0], distance: 2.0, fov: 30, modelX: 0 },
  listening: { target: [0, 1.1, 0], distance: 2.2, fov: 30, modelX: 0.1 },
  thinking: { target: [0, 1.1, 0], distance: 2.2, fov: 30, modelX: 0.1 },
  speaking: { target: [0, 1.25, 0], distance: 1.6, fov: 30, modelX: 0 },
};

class ConfigError extends Error {}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function requireNumber(v: unknown, where: string): number {
  if (typeof v !== "number" || !Number.isFinite(v)) {
    throw new ConfigError(`display.json: ${where} must be a number, got ${JSON.stringify(v)}`);
  }
  return v;
}

function parseExpressions(raw: unknown): ExpressionTable {
  const table: ExpressionTable = { neutral: {} };
  if (!isRecord(raw)) return table;
  for (const [name, weights] of Object.entries(raw)) {
    if (!isRecord(weights)) throw new ConfigError(`display.json: expressions.${name} must be an object`);
    table[name] = Object.fromEntries(
      Object.entries(weights).map(([k, w]) => [k, requireNumber(w, `expressions.${name}.${k}`)]),
    );
  }
  return table;
}

function parseFraming(raw: unknown, base: Framing, state: string): Framing {
  if (!isRecord(raw)) return base;
  const out: Framing = { ...base, target: [...base.target] };
  if (raw.target !== undefined) {
    if (!Array.isArray(raw.target) || raw.target.length !== 3) {
      throw new ConfigError(`display.json: framing.${state}.target must be [x, y, z]`);
    }
    out.target = [
      requireNumber(raw.target[0], `framing.${state}.target[0]`),
      requireNumber(raw.target[1], `framing.${state}.target[1]`),
      requireNumber(raw.target[2], `framing.${state}.target[2]`),
    ];
  }
  for (const key of ["distance", "fov", "modelX"] as const) {
    if (raw[key] !== undefined) out[key] = requireNumber(raw[key], `framing.${state}.${key}`);
  }
  return out;
}

function parseAvatar(raw: Record<string, unknown>): AvatarChoice {
  if (raw.vrm !== undefined && (typeof raw.vrm !== "string" || raw.vrm === "")) {
    throw new ConfigError("display.json: vrm must be the path of a VRM file under ADRIA_HOME");
  }
  const vrm = typeof raw.vrm === "string" ? raw.vrm : null;
  const avatar = raw.avatar ?? (vrm ? "vrm" : "placeholder");
  if (avatar === "placeholder") return { avatar };
  if (avatar !== "vrm") {
    throw new ConfigError(`display.json: avatar must be "placeholder" or "vrm", got ${JSON.stringify(avatar)}`);
  }
  if (!vrm) {
    throw new ConfigError('display.json: avatar "vrm" needs vrm (path of the VRM file under ADRIA_HOME)');
  }
  return { avatar, vrm };
}

export function parseDisplayConfig(raw: unknown): DisplayConfig {
  if (!isRecord(raw)) throw new ConfigError("display.json must be a JSON object");
  const framingRaw = isRecord(raw.framing) ? raw.framing : {};
  const frame = (s: ConversationState) => parseFraming(framingRaw[s], DEFAULT_FRAMING[s], s);
  const framing: Record<ConversationState, Framing> = {
    idle: frame("idle"),
    listening: frame("listening"),
    thinking: frame("thinking"),
    speaking: frame("speaking"),
  };
  const lip = isRecord(raw.lipSync) ? raw.lipSync : {};
  return {
    ...parseAvatar(raw),
    expressions: parseExpressions(raw.expressions),
    lipSync: {
      expression: typeof lip.expression === "string" ? lip.expression : "aa",
      fallbackHz: lip.fallbackHz === undefined ? 4 : requireNumber(lip.fallbackHz, "lipSync.fallbackHz"),
    },
    framing,
    transitionSec:
      raw.transitionSec === undefined ? 0.8 : requireNumber(raw.transitionSec, "transitionSec"),
  };
}
