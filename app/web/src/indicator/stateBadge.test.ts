import { describe, expect, it } from "vitest";
import { STATES } from "../signals/parseSignals";
import { badgeFor } from "./stateBadge";

describe("badgeFor", () => {
  it("gives each state its own color", () => {
    expect(new Set(STATES.map((s) => badgeFor(s).color)).size).toBe(STATES.length);
  });

  it("gives each state its own icon", () => {
    expect(new Set(STATES.map((s) => badgeFor(s).icon)).size).toBe(STATES.length);
  });

  it("names the state for assistive technology", () => {
    expect(badgeFor("listening").label).toMatch(/きいて/);
  });
});
