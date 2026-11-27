import datetime as dt
import json

import pytest

from adria_harness.config import load_config
from adria_harness.conversation import Conversation
from adria_harness.memory import MemoryStore
from adria_harness.playqueue import PlayQueue
from adria_harness.sessions import SessionBook
from adria_harness.status import Metrics, Status
from adria_harness.transcript import TranscriptLog

PERSONA = """+++
[reply]
max_sentences = 2
+++
あなたは子ども向けのキャラクターです。
"""


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
    (tmp_path / "persona.md").write_text(PERSONA, encoding="utf-8")
    cfg = load_config(tmp_path)
    llm = FakeLLM()
    queue = PlayQueue(cfg.runtime_dir)
    memory = MemoryStore(cfg.memory_path)
    conv = Conversation(cfg, llm, queue, Status(cfg.runtime_dir), Metrics(cfg.runtime_dir),
                        sessions=SessionBook(idle_sec=300), memory=memory,
                        transcript=TranscriptLog(cfg.transcript_dir, 7))
    return {"cfg": cfg, "conv": conv, "llm": llm, "queue": queue, "memory": memory}


def drain(queue):
    items = []
    while (item := queue.pop()) is not None:
        items.append(item)
    return items


def system_prompt(llm, call=-1):
    return llm.calls[call][0]["content"]


def test_the_persona_is_the_system_prompt(env):
    env["conv"].respond("やあ")
    assert system_prompt(env["llm"]).startswith("あなたは子ども向け")


def test_memory_is_in_the_system_prompt(env):
    env["memory"].append(dt.date(2026, 11, 24), "- いちごがすき")
    env["conv"].respond("やあ")
    assert "- いちごがすき" in system_prompt(env["llm"])


def test_persona_edits_apply_to_the_next_reply(env):
    env["conv"].respond("やあ")
    env["cfg"].persona_path.write_text("あたらしいせってい", encoding="utf-8")
    env["conv"].respond("やあ")
    assert system_prompt(env["llm"]) == "あたらしいせってい"


def test_lines_carry_no_voice_override(env):
    env["conv"].respond("やあ")
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


def test_turn_is_written_to_the_transcript(env):
    env["conv"].respond("やあ")
    files = list(env["cfg"].transcript_dir.glob("*.jsonl"))
    entry = json.loads(files[0].read_text(encoding="utf-8"))
    assert (entry["user"], entry["reply"]) == ("やあ", "うん。いいね。")
