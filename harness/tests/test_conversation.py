import datetime as dt
import json

import pytest

from adria_harness.config import load_config
from adria_harness.conversation import Conversation
from adria_harness.memory import MemoryStore
from adria_harness.playqueue import PlayQueue
from adria_harness.sessions import SessionBook
from adria_harness.speaker import SpeakerMatch
from adria_harness.status import Metrics, Status
from adria_harness.transcript import TranscriptLog

CHILD = """+++
[voice]
reference = "kid-voice"
caption = "あかるい声"
[reply]
max_sentences = 2
+++
あなたは子ども向けのキャラクターです。
"""
PARENT = "あなたは大人向けのアシスタントです。"


class FakeLLM:
    def __init__(self, reply="うん。いいね。もっとはなそう。"):
        self.reply = reply
        self.calls: list[list[dict]] = []

    def is_loaded(self):
        return True

    def chat_stream(self, messages):
        self.calls.append(messages)
        yield from self.reply


@pytest.fixture
def env(tmp_path):
    (tmp_path / "personas").mkdir()
    (tmp_path / "personas" / "child.md").write_text(CHILD, encoding="utf-8")
    (tmp_path / "personas" / "parent.md").write_text(PARENT, encoding="utf-8")
    cfg = load_config(tmp_path)
    llm = FakeLLM()
    queue = PlayQueue(cfg.runtime_dir)
    ended = []
    memory = MemoryStore(cfg.memory_dir)
    conv = Conversation(cfg, llm, queue, Status(cfg.runtime_dir), Metrics(cfg.runtime_dir),
                        sessions=SessionBook(idle_sec=300), memory=memory,
                        transcript=TranscriptLog(cfg.transcript_dir, 7),
                        on_session_end=ended.append)
    return {"cfg": cfg, "conv": conv, "llm": llm, "queue": queue, "ended": ended,
            "memory": memory}


def drain(queue):
    items = []
    while (item := queue.pop()) is not None:
        items.append(item)
    return items


def system_prompt(llm, call=-1):
    return llm.calls[call][0]["content"]


def test_default_persona_is_used_without_a_speaker(env):
    env["conv"].respond("やあ")
    assert system_prompt(env["llm"]).startswith("あなたは子ども向け")


def test_named_persona_is_used(env):
    env["conv"].respond("やあ", persona_name="parent")
    assert system_prompt(env["llm"]).startswith("あなたは大人向け")


def test_persona_memory_is_in_the_system_prompt(env):
    env["memory"].append("child", dt.date(2026, 11, 24), "- いちごがすき")
    env["conv"].respond("やあ")
    assert "- いちごがすき" in system_prompt(env["llm"])


def test_other_persona_memory_is_not_in_the_system_prompt(env):
    env["memory"].append("parent", dt.date(2026, 11, 24), "- おとなのひみつ")
    env["conv"].respond("やあ")
    assert "おとなのひみつ" not in system_prompt(env["llm"])


def test_persona_edits_apply_to_the_next_reply(env):
    env["conv"].respond("やあ")
    (env["cfg"].persona_dir / "child.md").write_text("あたらしいせってい", encoding="utf-8")
    env["conv"].respond("やあ")
    assert system_prompt(env["llm"]) == "あたらしいせってい"


def test_lines_carry_the_persona_voice(env):
    env["conv"].respond("やあ")
    assert drain(env["queue"])[0]["voice"] == "kid-voice"


def test_lines_carry_the_persona_caption(env):
    env["conv"].respond("やあ")
    assert drain(env["queue"])[0]["caption"] == "あかるい声"


def test_persona_without_voice_settings_uses_the_global_voice(env):
    env["conv"].respond("やあ", persona_name="parent")
    assert "voice" not in drain(env["queue"])[0]


def test_reply_is_cut_at_the_persona_limit(env):
    env["conv"].respond("やあ")
    assert len(drain(env["queue"])) == 2


def test_returned_reply_is_what_was_spoken(env):
    assert env["conv"].respond("やあ") == "うん。いいね。"


def test_history_holds_only_what_was_spoken(env):
    env["conv"].respond("やあ")
    env["conv"].respond("それで")
    assert env["llm"].calls[1][2] == {"role": "assistant", "content": "うん。いいね。"}


def test_switching_persona_ends_the_previous_session(env):
    env["conv"].respond("やあ")
    env["conv"].respond("こんにちは", persona_name="parent")
    assert env["ended"][0].persona == "child"


def test_switching_persona_does_not_carry_history_over(env):
    env["conv"].respond("やあ")
    env["conv"].respond("こんにちは", persona_name="parent")
    assert len(env["llm"].calls[1]) == 2  # system + user only


def test_turn_is_written_to_the_transcript(env):
    env["conv"].respond("やあ", speaker=SpeakerMatch("mom", 0.8), persona_name="parent")
    files = list(env["cfg"].transcript_dir.glob("*.jsonl"))
    entry = json.loads(files[0].read_text(encoding="utf-8"))
    assert (entry["persona"], entry["speaker"], entry["user"]) == ("parent", "mom", "やあ")
