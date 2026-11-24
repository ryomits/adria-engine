"""Mouth-openness curve from audio, for lip sync on the display side.

The harness computes the curve once per line and embeds it in ``now_playing``;
the display app only samples it by elapsed time. The offline check tool
(``tools/lipsync_check.py``) uses this same function, so what is tuned offline
is exactly what the character does.

Steps: short-time RMS -> per-line normalization -> perceptual curve ->
noise gate -> attack/release smoothing -> clip.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class LipSyncParams:
    fps: int = 100
    window_ms: float = 20.0
    attack_ms: float = 30.0  # time constant while opening
    release_ms: float = 80.0  # time constant while closing
    gamma: float = 0.6  # < 1 opens the mouth more for mid-level sounds
    gate_rms: float = 0.01  # absolute RMS below which the frame counts as silence
    gate_level: float = 0.1  # level (relative to the line's loud parts) treated as silence
    ref_floor: float = 0.02  # keeps quiet lines from being over-amplified
    max_open: float = 0.9
    snap_below: float = 0.02  # fully close once nearly closed in silence


@dataclass(frozen=True)
class MouthCurve:
    fps: int
    values: list[float]

    def to_json(self) -> dict:
        return {"fps": self.fps, "values": self.values}


def frame_rms(audio: np.ndarray, sr: int, params: LipSyncParams) -> np.ndarray:
    """RMS of a window centred on each output frame."""
    n_frames = int(round(len(audio) / sr * params.fps))
    half = max(1, int(sr * params.window_ms / 1000 / 2))
    padded = np.pad(audio.astype(np.float64), (half, half))
    csum = np.concatenate([[0.0], np.cumsum(padded**2)])
    centres = (np.arange(n_frames) * sr / params.fps).astype(int) + half
    lo, hi = centres - half, centres + half
    return np.sqrt((csum[hi] - csum[lo]) / (hi - lo))


def mouth_curve(audio: np.ndarray, sr: int, params: LipSyncParams | None = None) -> MouthCurve:
    params = params or LipSyncParams()
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    rms = frame_rms(audio, sr, params)
    if len(rms) == 0:
        return MouthCurve(params.fps, [])
    ref = max(float(np.percentile(rms, 95)), params.ref_floor)
    level = np.clip(rms / ref, 0.0, 1.0)
    target = level**params.gamma
    target[(rms < params.gate_rms) | (level < params.gate_level)] = 0.0

    dt_ms = 1000 / params.fps
    k_attack = 1 - np.exp(-dt_ms / params.attack_ms)
    k_release = 1 - np.exp(-dt_ms / params.release_ms)
    out = np.empty_like(target)
    y = 0.0
    for i, t in enumerate(target):
        y += (t - y) * (k_attack if t > y else k_release)
        if t == 0.0 and y < params.snap_below:
            y = 0.0
        out[i] = y
    out = np.minimum(out, params.max_open)
    return MouthCurve(params.fps, [round(float(v), 3) for v in out])
