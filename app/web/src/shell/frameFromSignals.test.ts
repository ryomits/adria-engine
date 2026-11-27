import { describe, expect, it } from "vitest";
import type { NowPlaying } from "../signals/parseSignals";
import { frameFromSignals } from "./frameFromSignals";

const line: NowPlaying = {
  id: "t-0",
  expression: "happy",
  startedAt: 100,
  duration: 1,
  mouth: { fps: 10, values: [0, 0.8, 0.4] },
};

describe("frameFromSignals", () => {
  it("passes the state through", () => {
    expect(frameFromSignals("thinking", null, 0, 4).state).toBe("thinking");
  });

  it("keeps the mouth closed when nothing is playing", () => {
    expect(frameFromSignals("speaking", null, 0, 4).mouth).toBe(0);
  });

  it("uses the neutral expression when nothing is playing", () => {
    expect(frameFromSignals("idle", null, 0, 4).expression).toBe("neutral");
  });

  it("uses the expression of the line being played", () => {
    expect(frameFromSignals("speaking", line, 100, 4).expression).toBe("happy");
  });

  it("samples the mouth curve by the time since the line started", () => {
    expect(frameFromSignals("speaking", line, 100.1, 4).mouth).toBeCloseTo(0.8);
  });

  it("closes the mouth after a line without a curve has ended", () => {
    expect(frameFromSignals("speaking", { ...line, mouth: null }, 102, 4).mouth).toBe(0);
  });
});
