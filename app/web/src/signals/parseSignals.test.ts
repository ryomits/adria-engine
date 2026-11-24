import { describe, expect, it } from "vitest";
import { parseNowPlaying, parseState } from "./parseSignals";

describe("parseState", () => {
  it("returns the state name from a state file", () => {
    expect(parseState({ state: "thinking", since: 1 })).toBe("thinking");
  });

  it("falls back to idle for an unknown state", () => {
    expect(parseState({ state: "dancing" })).toBe("idle");
  });

  it("falls back to idle for a malformed file", () => {
    expect(parseState("garbage")).toBe("idle");
  });
});

describe("parseNowPlaying", () => {
  const playing = {
    playing: true,
    id: "t1-0",
    text: "こんにちは",
    x_expression: "happy",
    started_at: 100.5,
    duration: 2,
    mouth: { fps: 100, values: [0, 0.5, 1] },
  };

  it("returns null when nothing is playing", () => {
    expect(parseNowPlaying({ playing: false })).toBeNull();
  });

  it("keeps the line id", () => {
    expect(parseNowPlaying(playing)?.id).toBe("t1-0");
  });

  it("reads the expression from the x_expression key", () => {
    expect(parseNowPlaying(playing)?.expression).toBe("happy");
  });

  it("reads the start time", () => {
    expect(parseNowPlaying(playing)?.startedAt).toBe(100.5);
  });

  it("reads the mouth curve", () => {
    expect(parseNowPlaying(playing)?.mouth?.values).toEqual([0, 0.5, 1]);
  });

  it("drops a mouth curve with non-numeric values", () => {
    const bad = { ...playing, mouth: { fps: 100, values: ["x"] } };
    expect(parseNowPlaying(bad)?.mouth).toBeNull();
  });

  it("defaults the expression to neutral", () => {
    const { x_expression: _, ...noExpr } = playing;
    expect(parseNowPlaying(noExpr)?.expression).toBe("neutral");
  });

  it("returns null when the start time is missing", () => {
    const { started_at: _, ...noStart } = playing;
    expect(parseNowPlaying(noStart)).toBeNull();
  });
});
