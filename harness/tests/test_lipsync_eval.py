import numpy as np

from adria_harness.lipsync import LipSyncParams, frame_rms, mouth_curve, normalized_level
from adria_harness.lipsync_eval import closed_in_silence, flap_rate, onset_lags_ms

SR = 16000
P = LipSyncParams()


def burst_train(n: int = 4, on: float = 0.25, off: float = 0.35) -> np.ndarray:
    t = np.arange(int(on * SR)) / SR
    burst = (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    gap = np.zeros(int(off * SR), dtype=np.float32)
    return np.concatenate([gap] + [np.concatenate([burst, gap]) for _ in range(n)])


def evaluate(audio):
    return frame_rms(audio, SR, P), np.array(mouth_curve(audio, SR, P).values)


def test_onset_lag_is_measured_for_every_burst():
    rms, mouth = evaluate(burst_train(n=4))
    assert len(onset_lags_ms(rms, mouth, P)) == 4


def test_onset_lag_of_clean_bursts_is_short():
    rms, mouth = evaluate(burst_train())
    assert max(onset_lags_ms(rms, mouth, P)) <= 50


def test_mouth_is_closed_throughout_silences():
    rms, mouth = evaluate(burst_train())
    assert closed_in_silence(rms, mouth, P) == 1.0


def test_closed_in_silence_detects_an_open_mouth_in_a_pause():
    rms, mouth = evaluate(burst_train())
    mouth[-10:] = 0.5  # mouth left open at the end of the trailing silence
    assert closed_in_silence(rms, mouth, P) < 1.0


def test_onset_lag_is_measured_from_audible_level_not_from_the_gate():
    # A soft consonant: the sound fades in over 150 ms before it is clearly audible.
    t = np.arange(int(0.6 * SR)) / SR
    ramp = np.minimum(t / 0.15, 1.0)
    audio = np.concatenate([np.zeros(SR // 2), 0.3 * ramp * np.sin(2 * np.pi * 220 * t)])
    rms, mouth = evaluate(audio.astype(np.float32))
    assert max(onset_lags_ms(rms, mouth, P)) <= 50


def steady(n=200, value=0.6):
    return np.full(n, value)


def test_flap_rate_is_zero_for_syllable_rate_motion():
    t = np.arange(200) / P.fps
    mouth = 0.4 + 0.3 * np.sin(2 * np.pi * 6 * t)  # 6 openings per second
    assert flap_rate(steady(), mouth, P) == 0.0


def test_flap_rate_counts_jitter_on_a_steady_sound():
    mouth = np.tile([0.3, 0.5], 100)  # flips every 10 ms while the level is constant
    assert flap_rate(steady(), mouth, P) > 10


def test_flap_rate_ignores_fast_moves_that_follow_large_level_changes():
    level = np.tile([0.9, 0.2], 100)  # the sound itself drops sharply (consonants)
    mouth = np.tile([0.8, 0.6], 100)
    assert flap_rate(level, mouth, P) == 0.0


def test_normalized_level_is_one_for_the_loud_parts():
    rms, _ = evaluate(burst_train())
    assert normalized_level(rms, P).max() == 1.0
