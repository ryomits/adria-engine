import stat

import numpy as np
import pytest

from adria_harness.persona import PersonaError
from adria_harness.speaker import (
    EnrollmentError,
    SpeakerIdentifier,
    SpeakerMatch,
    VoiceprintStore,
    enroll_voiceprint,
    match_voiceprint,
    persona_for,
)

SR = 16000


def unit(*v):
    a = np.array(v, dtype=np.float32)
    return a / np.linalg.norm(a)


PRINTS = {"mom": unit(1, 0, 0), "dad": unit(0, 1, 0)}


# ---- matching ----

def test_close_voice_matches_the_enrolled_speaker():
    assert match_voiceprint(unit(1, 0.1, 0), PRINTS, threshold=0.6, margin=0.1).speaker == "mom"


def test_match_reports_the_similarity():
    match = match_voiceprint(unit(1, 0, 0), PRINTS, threshold=0.6, margin=0.1)
    assert match.score == pytest.approx(1.0)


def test_voice_below_the_threshold_is_unknown():
    assert match_voiceprint(unit(0, 0, 1), PRINTS, threshold=0.6, margin=0.1).speaker is None


def test_ambiguous_voice_is_unknown():
    # Equally close to two speakers (e.g. mother and daughter): do not guess.
    assert match_voiceprint(unit(1, 1, 0.2), PRINTS, threshold=0.6, margin=0.1).speaker is None


def test_nobody_enrolled_means_unknown():
    assert match_voiceprint(unit(1, 0, 0), {}, threshold=0.6, margin=0.1).speaker is None


# ---- persona routing ----

def test_known_speaker_gets_the_mapped_persona():
    match = SpeakerMatch("mom", 0.9)
    assert persona_for(match, {"mom": "parent"}, default="child") == "parent"


def test_unknown_speaker_falls_back_to_the_default_persona():
    assert persona_for(SpeakerMatch(None, 0.2), {"mom": "parent"}, default="child") == "child"


def test_enrolled_but_unmapped_speaker_falls_back_to_the_default_persona():
    assert persona_for(SpeakerMatch("guest", 0.9), {"mom": "parent"}, default="child") == "child"


def test_missing_match_falls_back_to_the_default_persona():
    assert persona_for(None, {"mom": "parent"}, default="child") == "child"


# ---- store ----

def test_voiceprint_round_trips(tmp_path):
    store = VoiceprintStore(tmp_path)
    store.save("mom", unit(1, 2, 3))
    assert np.allclose(store.load_all()["mom"], unit(1, 2, 3))


def test_voiceprint_file_is_owner_only(tmp_path):
    VoiceprintStore(tmp_path).save("mom", unit(1, 2, 3))
    assert stat.S_IMODE((tmp_path / "mom.npy").stat().st_mode) == 0o600


def test_voiceprint_name_must_be_safe(tmp_path):
    with pytest.raises(PersonaError):
        VoiceprintStore(tmp_path).save("../mom", unit(1, 2, 3))


def test_voiceprint_can_be_removed(tmp_path):
    store = VoiceprintStore(tmp_path)
    store.save("mom", unit(1, 2, 3))
    store.remove("mom")
    assert store.load_all() == {}


def test_empty_store_loads_nothing(tmp_path):
    assert VoiceprintStore(tmp_path / "missing").load_all() == {}


# ---- enrollment ----

class FakeEmbedder:
    """Embeds by the mean amplitude, so the test controls the direction."""

    def __call__(self, audio: np.ndarray) -> np.ndarray:
        return unit(float(audio.mean()), 1.0, 0.0)


def seconds(n, value=0.5):
    return np.full(int(n * SR), value, dtype=np.float32)


def test_enrollment_averages_the_segment_embeddings():
    vp = enroll_voiceprint([seconds(6, 1.0), seconds(6, -1.0)], FakeEmbedder(), min_total_sec=10)
    assert np.allclose(vp, unit(0, 1, 0), atol=1e-6)


def test_enrollment_needs_enough_speech():
    with pytest.raises(EnrollmentError):
        enroll_voiceprint([seconds(3)], FakeEmbedder(), min_total_sec=10)


def test_enrollment_voiceprint_is_unit_length():
    vp = enroll_voiceprint([seconds(6), seconds(6)], FakeEmbedder(), min_total_sec=10)
    assert np.linalg.norm(vp) == pytest.approx(1.0)


# ---- identifier ----

class CountingEmbedder(FakeEmbedder):
    def __init__(self):
        self.calls = 0

    def __call__(self, audio):
        self.calls += 1
        return super().__call__(audio)


def identifier(tmp_path, embedder, min_audio_sec=1.0):
    store = VoiceprintStore(tmp_path)
    store.save("mom", unit(0.5, 1.0, 0.0))
    return SpeakerIdentifier(embedder, store, threshold=0.6, margin=0.1,
                             min_audio_sec=min_audio_sec)


def test_identifier_matches_an_enrolled_voice(tmp_path):
    assert identifier(tmp_path, FakeEmbedder()).identify(seconds(2)).speaker == "mom"


def test_too_short_utterance_is_unknown(tmp_path):
    assert identifier(tmp_path, FakeEmbedder()).identify(seconds(0.5)).speaker is None


def test_too_short_utterance_is_not_embedded(tmp_path):
    embedder = CountingEmbedder()
    identifier(tmp_path, embedder).identify(seconds(0.5))
    assert embedder.calls == 0


def test_identifier_sees_new_enrollments_without_restart(tmp_path):
    ident = identifier(tmp_path, FakeEmbedder())
    ident.identify(seconds(2))
    VoiceprintStore(tmp_path).save("dad", unit(-0.5, 1.0, 0.0))
    assert ident.identify(seconds(2, value=-0.5)).speaker == "dad"
