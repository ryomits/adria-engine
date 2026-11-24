import json

from adria_harness.status import Status


def state(tmp_path):
    return json.loads((tmp_path / "state").read_text())["state"]


def test_idle_by_default(tmp_path):
    Status(tmp_path)
    assert state(tmp_path) == "idle"


def test_preparing_a_reply_counts_as_thinking(tmp_path):
    s = Status(tmp_path)
    s.update(preparing=True)
    assert state(tmp_path) == "thinking"


def test_speaking_wins_over_preparing(tmp_path):
    s = Status(tmp_path)
    s.update(preparing=True, speaking=True)
    assert state(tmp_path) == "speaking"


def test_listening_while_the_child_speaks(tmp_path):
    s = Status(tmp_path)
    s.update(listening=True)
    assert state(tmp_path) == "listening"
