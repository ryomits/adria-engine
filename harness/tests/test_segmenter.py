import numpy as np

from adria_harness.config import STTConfig
from adria_harness.stt import BLOCK, UtteranceSegmenter


class ScriptedVAD:
    """Emits start/end events at fixed block indexes."""

    def __init__(self, events: dict[int, dict]):
        self.events = events
        self.i = 0
        self.resets = 0

    def __call__(self, block):
        event = self.events.get(self.i)
        self.i += 1
        return event

    def reset(self):
        self.resets += 1


def blocks(n):
    return [np.full(BLOCK, 0.1, dtype=np.float32) for _ in range(n)]


def run(vad, stream, **cfg):
    return list(UtteranceSegmenter(STTConfig(**cfg), vad).segment(stream))


def test_yields_one_utterance_between_start_and_end():
    assert len(run(ScriptedVAD({5: {"start": 0}, 30: {"end": 0}}), blocks(40))) == 1


def test_utterance_includes_preroll_before_start():
    (audio, _), = run(ScriptedVAD({12: {"start": 0}, 30: {"end": 0}}), blocks(40))
    # 10 preroll blocks (incl. the start block) + 18 more up to the end block
    assert len(audio) == 28 * BLOCK


def test_muted_block_discards_partial_utterance():
    stream = blocks(10) + [None] + blocks(30)
    assert run(ScriptedVAD({5: {"start": 0}, 20: {"end": 0}}), stream) == []


def test_too_short_utterance_is_dropped():
    assert run(ScriptedVAD({0: {"start": 0}, 2: {"end": 0}}), blocks(10),
               min_utterance_sec=0.35) == []
