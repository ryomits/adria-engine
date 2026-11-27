import { describe, expect, it } from "vitest";
import { parseDisplayConfig } from "./parseDisplayConfig";

describe("parseDisplayConfig", () => {
  it("uses the placeholder character without a VRM", () => {
    expect(parseDisplayConfig({}).avatar).toBe("placeholder");
  });

  it("uses the VRM avatar when a VRM is set", () => {
    expect(parseDisplayConfig({ vrm: "avatars/a.vrm" }).avatar).toBe("vrm");
  });

  it("can choose the placeholder although a VRM is set", () => {
    expect(parseDisplayConfig({ vrm: "avatars/a.vrm", avatar: "placeholder" }).avatar).toBe(
      "placeholder",
    );
  });

  it("requires the VRM path for the VRM avatar", () => {
    expect(() => parseDisplayConfig({ avatar: "vrm" })).toThrow(/vrm/);
  });

  it("rejects an unknown avatar", () => {
    expect(() => parseDisplayConfig({ avatar: "robot" })).toThrow(/avatar/);
  });

  it("keeps the VRM path", () => {
    const cfg = parseDisplayConfig({ vrm: "avatars/a.vrm" });
    expect(cfg.avatar === "vrm" ? cfg.vrm : null).toBe("avatars/a.vrm");
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
