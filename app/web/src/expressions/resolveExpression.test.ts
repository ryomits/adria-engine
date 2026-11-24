import { describe, expect, it } from "vitest";
import { resolveExpression } from "./resolveExpression";

describe("resolveExpression", () => {
  const table = { neutral: {}, happy: { happy: 1 }, shy: { happy: 0.4, relaxed: 0.6 } };

  it("returns the VRM expression weights for a known name", () => {
    expect(resolveExpression(table, "shy")).toEqual({ happy: 0.4, relaxed: 0.6 });
  });

  it("returns neutral weights for an unknown name", () => {
    expect(resolveExpression(table, "confused")).toEqual({});
  });
});
