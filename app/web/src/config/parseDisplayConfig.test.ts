import { describe, expect, it } from "vitest";
import { parseDisplayConfig } from "./parseDisplayConfig";

describe("parseDisplayConfig", () => {
  it("requires the VRM path", () => {
    expect(() => parseDisplayConfig({})).toThrow(/vrm/);
  });

  it("keeps the VRM path", () => {
    expect(parseDisplayConfig({ vrm: "avatars/a.vrm" }).vrm).toBe("avatars/a.vrm");
  });

  it("provides framing for every state by default", () => {
    expect(Object.keys(parseDisplayConfig({ vrm: "a.vrm" }).framing).sort()).toEqual(
      ["idle", "listening", "speaking", "thinking"],
    );
  });

  it("overrides only the given framing fields", () => {
    const cfg = parseDisplayConfig({ vrm: "a.vrm", framing: { speaking: { distance: 0.9 } } });
    expect(cfg.framing.speaking.fov).toBe(parseDisplayConfig({ vrm: "a.vrm" }).framing.speaking.fov);
  });

  it("applies a framing override", () => {
    const cfg = parseDisplayConfig({ vrm: "a.vrm", framing: { speaking: { distance: 0.9 } } });
    expect(cfg.framing.speaking.distance).toBe(0.9);
  });

  it("rejects a non-numeric expression weight", () => {
    expect(() => parseDisplayConfig({ vrm: "a.vrm", expressions: { happy: { happy: "1" } } })).toThrow(
      /expressions\.happy\.happy/,
    );
  });
});
