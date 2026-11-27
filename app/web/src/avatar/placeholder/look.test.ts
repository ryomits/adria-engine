import { describe, expect, it } from "vitest";
import { STATES } from "../../signals/parseSignals";
import { placeholderLook } from "./look";

const times = Array.from({ length: 200 }, (_, i) => i * 0.05);

describe("placeholderLook", () => {
  it("gives each state its own body color", () => {
    expect(new Set(STATES.map((s) => placeholderLook(s, 0).color)).size).toBe(STATES.length);
  });

  it("keeps the bobbing small in every state", () => {
    const bobs = STATES.flatMap((s) => times.map((t) => Math.abs(placeholderLook(s, t).bob)));
    expect(Math.max(...bobs)).toBeLessThanOrEqual(0.03);
  });

  it("moves slowly (at most one cycle per second)", () => {
    expect(Math.max(...STATES.map((s) => placeholderLook(s, 0).hz))).toBeLessThanOrEqual(1);
  });

  it("closes the eyes while sleeping in standby", () => {
    expect(placeholderLook("idle", 0).eyeOpen).toBe(0);
  });

  it("shows sleeping z's only in standby", () => {
    expect(STATES.filter((s) => placeholderLook(s, 0).sleepZ > 0)).toEqual(["idle"]);
  });

  it("looks up and aside while thinking", () => {
    expect(placeholderLook("thinking", 0).gazeY).toBeLessThan(0);
  });

  it("shows a listening ring only while listening", () => {
    expect(STATES.filter((s) => placeholderLook(s, 0).ring > 0)).toEqual(["listening"]);
  });
});
