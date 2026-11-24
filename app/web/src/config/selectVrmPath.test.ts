import { describe, expect, it } from "vitest";
import { selectVrmPath } from "./selectVrmPath";

describe("selectVrmPath", () => {
  it("uses the configured model without an override", () => {
    expect(selectVrmPath("avatars/a.vrm", null)).toBe("avatars/a.vrm");
  });

  it("uses an override that names a model under avatars/", () => {
    expect(selectVrmPath("avatars/a.vrm", "avatars/b.vrm")).toBe("avatars/b.vrm");
  });

  it("ignores an override outside avatars/", () => {
    expect(selectVrmPath("avatars/a.vrm", "../config.toml")).toBe("avatars/a.vrm");
  });
});
