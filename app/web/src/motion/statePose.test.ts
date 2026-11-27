import { describe, expect, it } from "vitest";
import { STATES } from "../signals/parseSignals";
import { statePose } from "./statePose";

const times = Array.from({ length: 400 }, (_, i) => i * 0.05);

describe("statePose", () => {
  it("closes the eyes while sleeping in standby", () => {
    expect(statePose("idle", 0).eyesClosed).toBe(1);
  });

  it("opens the eyes in a conversation", () => {
    const awake = STATES.filter((s) => s !== "idle");
    expect(Math.max(...awake.map((s) => statePose(s, 0).eyesClosed))).toBe(0);
  });

  it("does not blink while asleep", () => {
    expect(statePose("idle", 0).blinks).toBe(false);
  });

  it("blinks while awake", () => {
    expect(statePose("listening", 0).blinks).toBe(true);
  });

  it("lets the head droop forward while asleep", () => {
    expect(statePose("idle", 0).headPitch).toBeGreaterThan(statePose("listening", 0).headPitch + 0.15);
  });

  it("breathes more slowly while asleep", () => {
    expect(statePose("idle", 0).breathSec).toBeGreaterThan(statePose("listening", 0).breathSec);
  });

  it("breathes more deeply while asleep", () => {
    expect(statePose("idle", 0).breathDepth).toBeGreaterThan(statePose("listening", 0).breathDepth);
  });

  it("looks up while thinking", () => {
    expect(statePose("thinking", 0).headPitch).toBeLessThan(0);
  });

  it("smiles a little while listening", () => {
    expect(statePose("listening", 0).mood.happy).toBeGreaterThan(0);
  });

  it("keeps every head angle small", () => {
    const angles = STATES.flatMap((s) =>
      times.map((t) => {
        const p = statePose(s, t);
        return Math.max(Math.abs(p.headPitch), Math.abs(p.headYaw), Math.abs(p.headRoll));
      }),
    );
    expect(Math.max(...angles)).toBeLessThanOrEqual(0.35);
  });
});
