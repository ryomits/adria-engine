"""Proxy metrics for judging a lip-sync curve offline.

These approximate the acceptance criteria (follows syllable onsets without a
visible delay, closes in silence, no high-frequency flapping). They are
proxies: the final judgement of naturalness is made by a person on the Mac.
"""

from __future__ import annotations

import numpy as np

from .lipsync import LipSyncParams, normalized_level

__all__ = [
    "closed_in_silence", "flap_rate", "normalized_level", "onset_lags_ms", "rapid_reversal_rate",
]

OPEN_THRESHOLD = 0.3  # mouth value that counts as visibly open
MIN_GAP_FRAMES = 5  # quiet frames required before a new onset
MAX_LAG_MS = 300.0  # an onset not followed by an opening within this counts as this lag
SETTLE_MS = 250.0  # after speech ends, the mouth may still be closing for this long
FLAP_WINDOW_MS = 50.0  # reversals closer than this are flapping, not syllables
FLAP_MIN_SWING = 0.08
# A fast move counts as flapping only if the sound itself changed less than this;
# fast moves that follow a large level change (consonants) are real articulation.
FLAP_MAX_LEVEL_CHANGE = 0.2


def _voiced(rms: np.ndarray, p: LipSyncParams) -> np.ndarray:
    return rms >= p.gate_rms


def onset_lags_ms(rms: np.ndarray, mouth: np.ndarray, p: LipSyncParams) -> list[float]:
    """Delay from each syllable onset until the mouth is visibly open.

    An onset is where the sound becomes clearly audible (normalized level
    reaches OPEN_THRESHOLD) after a quiet stretch, so a soft consonant that
    fades in is measured from when it is heard rather than from near-silence.
    """
    level = normalized_level(rms, p)
    loud = level >= OPEN_THRESHOLD
    limit = int(MAX_LAG_MS * p.fps / 1000)
    lags = []
    for i in range(MIN_GAP_FRAMES, len(loud)):
        if not loud[i] or loud[i - MIN_GAP_FRAMES:i].any():
            continue
        opened = np.flatnonzero(mouth[i:i + limit] >= OPEN_THRESHOLD)
        lags.append(opened[0] * 1000 / p.fps if len(opened) else MAX_LAG_MS)
    return lags


def closed_in_silence(rms: np.ndarray, mouth: np.ndarray, p: LipSyncParams) -> float:
    """Fraction of settled silent frames in which the mouth is fully closed."""
    voiced = _voiced(rms, p)
    settle = int(SETTLE_MS * p.fps / 1000)
    last_voiced = -settle - 1
    checked = closed = 0
    for i, v in enumerate(voiced):
        if v:
            last_voiced = i
            continue
        if i - last_voiced > settle:
            checked += 1
            closed += mouth[i] == 0.0
    return 1.0 if checked == 0 else closed / checked


def flap_rate(level: np.ndarray, mouth: np.ndarray, p: LipSyncParams) -> float:
    """Fast open/close reversals per second that the sound itself does not explain."""
    return sum(1 for a, b in _rapid_reversals(mouth, p)
               if abs(level[b] - level[a]) < FLAP_MAX_LEVEL_CHANGE) / (len(mouth) / p.fps)


def rapid_reversal_rate(mouth: np.ndarray, p: LipSyncParams) -> float:
    """All fast reversals per second, including ones that follow the sound (for reference)."""
    return len(_rapid_reversals(mouth, p)) / (len(mouth) / p.fps)


def _rapid_reversals(mouth: np.ndarray, p: LipSyncParams) -> list[tuple[int, int]]:
    d = np.diff(mouth)
    extrema = [i + 1 for i in range(len(d) - 1) if d[i] * d[i + 1] < 0]
    window = FLAP_WINDOW_MS * p.fps / 1000
    return [(a, b) for a, b in zip(extrema, extrema[1:], strict=False)
            if b - a < window and abs(mouth[b] - mouth[a]) > FLAP_MIN_SWING]
