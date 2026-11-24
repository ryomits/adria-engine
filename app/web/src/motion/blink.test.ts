import { describe, expect, it } from "vitest";
import { blinkWeight, nextBlinkInterval } from "./blink";

describe("blinkWeight", () => {
  it("is open before the blink starts", () => {
    expect(blinkWeight(-0.01)).toBe(0);
  });

  it("is fully closed at the middle of the blink", () => {
    expect(blinkWeight(0.075)).toBe(1);
  });

  it("is open again after the blink", () => {
    expect(blinkWeight(0.2)).toBe(0);
  });
});

describe("nextBlinkInterval", () => {
  it("waits at least 2 seconds", () => {
    expect(nextBlinkInterval(0)).toBe(2);
  });

  it("waits at most 6 seconds", () => {
    expect(nextBlinkInterval(0.999999)).toBeLessThan(6);
  });
});
