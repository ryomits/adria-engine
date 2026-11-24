import io
import json
import time

import numpy as np
import pytest
import soundfile as sf

from adria_harness.player import Player
from adria_harness.playqueue import PlayQueue
from adria_harness.status import Metrics, Status


class FakeTTS:
    """Returns a 0.3 s tone for any text."""

    def __init__(self):
        self.calls: list[dict] = []

    def synthesize(self, text: str, voice: str | None = None, caption: str | None = None) -> bytes:
        self.calls.append({"text": text, "voice": voice, "caption": caption})
        sr = 16000
        t = np.arange(int(0.3 * sr)) / sr
        buf = io.BytesIO()
        sf.write(buf, (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), sr, format="WAV")
        return buf.getvalue()


def wait_for_playing(path, timeout=3.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        data = json.loads(path.read_text())
        if data.get("playing"):
            return data
        time.sleep(0.01)
    raise AssertionError("now_playing never reported a playing line")


@pytest.fixture
def playing_line(tmp_path):
    queue = PlayQueue(tmp_path)
    status = Status(tmp_path)
    player = Player(queue, FakeTTS(), status, Metrics(tmp_path), mute=True)
    player.start()
    queue.push({"id": "t-0", "turn_id": "t", "seq": 0, "text": "やあ", "x_expression": "happy"})
    try:
        yield wait_for_playing(tmp_path / "now_playing")
    finally:
        player.stop()


def test_now_playing_carries_mouth_curve_at_100fps(playing_line):
    assert playing_line["mouth"]["fps"] == 100


def test_mouth_curve_covers_the_line(playing_line):
    assert len(playing_line["mouth"]["values"]) == 30


def test_now_playing_keeps_x_keys_for_the_display(playing_line):
    assert playing_line["x_expression"] == "happy"


class LatentPlayer(Player):
    """Simulates an output device that adds 0.2 s before the sound is heard."""

    def _start_output(self, data, sr) -> float:
        return 0.2


def test_started_at_includes_output_latency(tmp_path):
    queue = PlayQueue(tmp_path)
    player = LatentPlayer(queue, FakeTTS(), Status(tmp_path), Metrics(tmp_path), mute=True)
    player.start()
    try:
        before = time.time()
        queue.push({"id": "t-0", "turn_id": "t", "seq": 0, "text": "やあ"})
        line = wait_for_playing(tmp_path / "now_playing")
        assert line["started_at"] >= before + 0.2
    finally:
        player.stop()


class SlowTTS(FakeTTS):
    def synthesize(self, text: str, voice: str | None = None, caption: str | None = None) -> bytes:
        time.sleep(0.3)
        return super().synthesize(text, voice, caption)


def test_state_is_thinking_while_the_first_line_is_synthesized(tmp_path):
    queue = PlayQueue(tmp_path)
    player = Player(queue, SlowTTS(), Status(tmp_path), Metrics(tmp_path), mute=True)
    player.start()
    try:
        queue.push({"id": "t-0", "turn_id": "t", "seq": 0, "text": "やあ"})
        time.sleep(0.15)  # synthesis is still running
        assert json.loads((tmp_path / "state").read_text())["state"] == "thinking"
    finally:
        player.stop()


def test_line_voice_and_caption_are_passed_to_tts(tmp_path):
    queue = PlayQueue(tmp_path)
    tts = FakeTTS()
    player = Player(queue, tts, Status(tmp_path), Metrics(tmp_path), mute=True)
    player.start()
    try:
        queue.push({"id": "t-0", "turn_id": "t", "seq": 0, "text": "やあ",
                    "voice": "parent-voice", "caption": "おちついた声"})
        wait_for_playing(tmp_path / "now_playing")
        assert tts.calls[0] == {"text": "やあ", "voice": "parent-voice", "caption": "おちついた声"}
    finally:
        player.stop()
