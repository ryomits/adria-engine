import { describe, expect, it } from "vitest";
import { approach } from "./approach";

describe("approach", () => {
  it("moves toward the target without overshooting", () => {
    expect(approach({ current: 0, target: 1, dt: 0.016, tau: 0.3 })).toBeGreaterThan(0);
  });

  it("does not jump in a single frame", () => {
    expect(approach({ current: 0, target: 1, dt: 0.016, tau: 0.3 })).toBeLessThan(0.1);
  });

  it("gets within 5% after three time constants", () => {
    let v = 0;
    for (let t = 0; t < 0.9; t += 0.01) v = approach({ current: v, target: 1, dt: 0.01, tau: 0.3 });
    expect(v).toBeGreaterThan(0.95);
  });
});
