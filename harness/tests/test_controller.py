"""The harness side of the display link: control file in, state file out."""

import json

import pytest

from adria_harness.control import ControlInbox
from adria_harness.controller import Controller
from adria_harness.sessions import SessionBook
from adria_harness.status import Status
from adria_harness.switch import ConversationSwitch

TIMEOUT = 300


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture
def env(tmp_path):
    clock = Clock()
    status = Status(tmp_path)
    switch = ConversationSwitch(TIMEOUT, clock=clock,
                                on_change=lambda active: status.update(active=active))
    sessions = SessionBook(TIMEOUT, clock=clock)
    ended, quits = [], []
    controller = Controller(ControlInbox(tmp_path / "control.jsonl"), switch, sessions,
                            on_session_end=ended.append, on_quit=lambda: quits.append(1))
    seq = iter(range(1, 1000))

    def click(command="toggle"):
        with (tmp_path / "control.jsonl").open("a") as f:
            f.write(json.dumps({"seq": next(seq), "command": command}) + "\n")
        controller.tick()

    def state():
        return json.loads((tmp_path / "state").read_text())["state"]

    return {"clock": clock, "status": status, "switch": switch, "sessions": sessions,
            "ended": ended, "quits": quits, "controller": controller, "click": click,
            "state": state}


def test_standby_until_clicked(env):
    env["controller"].tick()
    assert env["state"]() == "idle"


def test_click_starts_listening(env):
    env["click"]()
    assert env["state"]() == "listening"


def test_second_click_goes_back_to_standby(env):
    env["click"]()
    env["click"]()
    assert env["state"]() == "idle"


def test_silence_timeout_goes_back_to_standby(env):
    env["click"]()
    env["clock"].now = TIMEOUT
    env["controller"].tick()
    assert env["state"]() == "idle"


def test_states_follow_a_whole_turn(env):
    seen = []
    env["click"]()
    seen.append(env["state"]())
    env["status"].add_thinking(+1)
    seen.append(env["state"]())
    env["status"].add_thinking(-1)
    env["status"].update(speaking=True)
    seen.append(env["state"]())
    env["status"].update(speaking=False)
    seen.append(env["state"]())
    assert seen == ["listening", "thinking", "speaking", "listening"]


def test_click_during_a_reply_returns_to_standby_after_it(env):
    env["click"]()
    env["status"].update(speaking=True)
    env["click"]()
    env["status"].update(speaking=False)
    assert env["state"]() == "idle"


def test_silence_timeout_ends_the_session(env):
    env["click"]()
    env["sessions"].record("やあ", "こんにちは。")
    env["clock"].now = TIMEOUT
    env["controller"].tick()
    assert env["ended"][0].turns == [("やあ", "こんにちは。")]


def test_click_to_standby_keeps_the_session(env):
    env["click"]()
    env["sessions"].record("やあ", "こんにちは。")
    env["click"]()
    assert env["ended"] == []


def test_quit_command_is_passed_on(env):
    env["click"]("quit")
    assert env["quits"] == [1]
