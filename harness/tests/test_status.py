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


def test_an_active_conversation_is_listening(tmp_path):
    s = Status(tmp_path)
    s.update(active=True)
    assert state(tmp_path) == "listening"


def test_thinking_wins_over_an_active_conversation(tmp_path):
    s = Status(tmp_path)
    s.update(active=True, preparing=True)
    assert state(tmp_path) == "thinking"


def test_standby_after_the_conversation_ends(tmp_path):
    s = Status(tmp_path)
    s.update(active=True)
    s.update(active=False)
    assert state(tmp_path) == "idle"
