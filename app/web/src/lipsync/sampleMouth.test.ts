import { describe, expect, it } from "vitest";
import { fallbackMouth, sampleMouth } from "./sampleMouth";

describe("sampleMouth", () => {
  const curve = { fps: 10, values: [0, 1, 0.5] };

  it("returns the value of the frame at the elapsed time", () => {
    expect(sampleMouth(curve, 0.1)).toBe(1);
  });

  it("interpolates between frames", () => {
    expect(sampleMouth(curve, 0.15)).toBeCloseTo(0.75);
  });

  it("returns 0 before playback starts", () => {
    expect(sampleMouth(curve, -0.05)).toBe(0);
  });

  it("returns 0 after the curve ends", () => {
    expect(sampleMouth(curve, 0.5)).toBe(0);
  });
});

describe("fallbackMouth", () => {
  it("starts closed", () => {
    expect(fallbackMouth(0, 4)).toBe(0);
  });

  it("never opens beyond 0.6", () => {
    const peak = Math.max(...Array.from({ length: 100 }, (_, i) => fallbackMouth(i / 100, 4)));
    expect(peak).toBeLessThanOrEqual(0.6);
  });
});
