import numpy as np
import pytest

from adria_harness.lipsync import LipSyncParams, mouth_curve

SR = 16000
FPS = 100


def tone(sec: float, amp: float = 0.3, hz: float = 220.0) -> np.ndarray:
    t = np.arange(int(sec * SR)) / SR
    return (amp * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def silence(sec: float) -> np.ndarray:
    return np.zeros(int(sec * SR), dtype=np.float32)


def frame(sec: float) -> int:
    return int(round(sec * FPS))


def test_curve_has_one_value_per_frame():
    assert len(mouth_curve(tone(1.0), SR).values) == FPS


def test_silence_keeps_mouth_closed():
    assert max(mouth_curve(silence(1.0), SR).values) == 0.0


def test_loud_sound_opens_mouth():
    curve = mouth_curve(np.concatenate([silence(0.2), tone(0.5)]), SR)
    assert curve.values[frame(0.5)] > 0.6


def test_opening_never_exceeds_max_open():
    params = LipSyncParams(max_open=0.8)
    assert max(mouth_curve(tone(1.0, amp=0.9), SR, params).values) <= 0.8


def test_mouth_follows_onset_within_50ms():
    audio = np.concatenate([silence(0.3), tone(0.5)])
    values = mouth_curve(audio, SR).values
    first_open = next(i for i, v in enumerate(values) if v > 0.3)
    assert (first_open - frame(0.3)) / FPS <= 0.05


def test_mouth_closes_fully_in_silence_after_speech():
    audio = np.concatenate([tone(0.4), silence(0.6)])
    assert mouth_curve(audio, SR).values[frame(0.8)] == 0.0


def test_small_volume_wobble_does_not_flap():
    # +-10% amplitude modulation at 12 Hz on a steady vowel
    t = np.arange(int(1.0 * SR)) / SR
    audio = (0.3 * (1 + 0.1 * np.sin(2 * np.pi * 12 * t)) * np.sin(2 * np.pi * 220 * t))
    values = np.array(mouth_curve(audio.astype(np.float32), SR).values[frame(0.2):])
    assert values.max() - values.min() < 0.15


def test_quiet_noise_is_gated_to_closed():
    rng = np.random.default_rng(0)
    noise = (0.002 * rng.standard_normal(SR)).astype(np.float32)
    assert max(mouth_curve(noise, SR).values) == 0.0


@pytest.mark.parametrize("sr", [16000, 44100, 48000])
def test_length_is_independent_of_sample_rate(sr):
    audio = np.zeros(int(0.5 * sr), dtype=np.float32)
    assert len(mouth_curve(audio, sr).values) == frame(0.5)
