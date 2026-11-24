const BLINK_SEC = 0.15;

/** Eyelid closure (0 = open, 1 = closed) ``t`` seconds after a blink starts. */
export function blinkWeight(t: number): number {
  if (t < 0 || t > BLINK_SEC) return 0;
  return 1 - Math.abs(t - BLINK_SEC / 2) / (BLINK_SEC / 2);
}

/** Seconds until the next blink, from a uniform random number in [0, 1). */
export function nextBlinkInterval(rand: number): number {
  return 2 + 4 * rand;
}
