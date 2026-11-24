/** Exponential smoothing toward ``target`` with time constant ``tau`` (frame-rate independent). */
export function approach(args: { current: number; target: number; dt: number; tau: number }): number {
  const { current, target, dt, tau } = args;
  return target + (current - target) * Math.exp(-dt / tau);
}
