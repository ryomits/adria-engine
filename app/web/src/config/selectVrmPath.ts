const AVATAR_PATH = /^avatars\/[^/]+\.vrm$/;

/** The configured model, or a `?vrm=avatars/x.vrm` override (development and offline checks). */
export function selectVrmPath(configured: string, override: string | null): string {
  return override !== null && AVATAR_PATH.test(override) ? override : configured;
}
