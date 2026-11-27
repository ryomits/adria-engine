import datetime as dt
import json

from adria_harness.memory import MemoryStore, Summarizer, build_system_prompt
from adria_harness.persona import MemorySpec, Persona
from adria_harness.sessions import Session

DAY = dt.date(2026, 11, 25)
CHILD = Persona("あなたは「テスト」です。",
                memory=MemorySpec(user_label="子ども", focus=("すきなもの", "やくそく")))


def session():
    return Session([("いちごがすき", "おいしいよね。")], last_activity=0.0)


class FakeLLM:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls: list[list[dict]] = []

    def __call__(self, messages, json_output=False):
        self.calls.append(messages)
        return self.replies.pop(0)


def items(*pairs):
    """LLM summary reply: (memo, evidence) pairs as JSON."""
    return json.dumps({"items": [{"memo": m, "evidence": e} for m, e in pairs]},
                      ensure_ascii=False)


STRAWBERRY = items(("いちごがすき", "いちごがすき"))


def summarizer(tmp_path, llm, max_chars=1000):
    store = MemoryStore(tmp_path / "memory" / "summary.md")
    return Summarizer(llm, store, max_chars=max_chars, persona=lambda: CHILD), store


# ---- store ----

def store_in(tmp_path):
    return MemoryStore(tmp_path / "memory" / "summary.md")


def test_memory_is_empty_before_anything_is_saved(tmp_path):
    assert store_in(tmp_path).read() == ""


def test_appended_summary_is_read_back(tmp_path):
    store = store_in(tmp_path)
    store.append(DAY, "- いちごがすき")
    assert "- いちごがすき" in store.read()


def test_appended_summary_is_dated(tmp_path):
    store = store_in(tmp_path)
    store.append(DAY, "- いちごがすき")
    assert "2026-11-25" in store.read()


def test_later_summaries_are_added_below(tmp_path):
    store = store_in(tmp_path)
    store.append(DAY, "- いちごがすき")
    store.append(DAY, "- いぬがすき")
    assert store.read().index("いちご") < store.read().index("いぬ")


# ---- system prompt ----

def test_system_prompt_without_memory_is_the_persona_prompt():
    assert build_system_prompt(CHILD, "") == CHILD.prompt


def test_system_prompt_includes_the_memory():
    assert "- いちごがすき" in build_system_prompt(CHILD, "- いちごがすき")


def test_system_prompt_starts_with_the_persona_prompt():
    assert build_system_prompt(CHILD, "- いちごがすき").startswith(CHILD.prompt)


# ---- summarizer ----

def test_session_summary_is_appended_to_its_persona(tmp_path):
    s, store = summarizer(tmp_path, FakeLLM(STRAWBERRY))
    s.summarize(session(), DAY)
    assert "- いちごがすき" in store.read()


def test_summary_prompt_contains_the_conversation(tmp_path):
    llm = FakeLLM(STRAWBERRY)
    s, _ = summarizer(tmp_path, llm)
    s.summarize(session(), DAY)
    assert "子ども: いちごがすき" in llm.calls[0][-1]["content"]


def test_summary_prompt_names_the_persona_focus(tmp_path):
    llm = FakeLLM(STRAWBERRY)
    s, _ = summarizer(tmp_path, llm)
    s.summarize(session(), DAY)
    assert "やくそく" in llm.calls[0][0]["content"]


def test_memo_without_evidence_in_the_conversation_is_dropped(tmp_path):
    # The model invents a friend that was never mentioned.
    s, store = summarizer(tmp_path, FakeLLM(items(("友達はたかし", "たかしくんとあそんだ"))))
    s.summarize(session(), DAY)
    assert store.read() == ""


def test_evidence_matches_despite_spacing_and_punctuation(tmp_path):
    s, store = summarizer(tmp_path, FakeLLM(items(("いちごがすき", "いちご、が すき！"))))
    s.summarize(session(), DAY)
    assert "- いちごがすき" in store.read()


def test_evidence_must_be_more_than_a_fragment(tmp_path):
    s, store = summarizer(tmp_path, FakeLLM(items(("いぬがすき", "が"))))
    s.summarize(session(), DAY)
    assert store.read() == ""


def test_nothing_is_saved_when_there_is_nothing_to_remember(tmp_path):
    s, store = summarizer(tmp_path, FakeLLM(items()))
    s.summarize(session(), DAY)
    assert store.read() == ""


def test_malformed_summary_saves_nothing(tmp_path):
    s, store = summarizer(tmp_path, FakeLLM("- いちごがすき"))
    s.summarize(session(), DAY)
    assert store.read() == ""


def long_session():
    return Session([("あ" * 60, "うん。")])


def test_large_memory_is_compacted(tmp_path):
    s, store = summarizer(tmp_path, FakeLLM(items(("あ" * 50, "あ" * 50)), "- まとめ"),
                          max_chars=40)
    s.summarize(long_session(), DAY)
    assert "- まとめ" in store.read()


def test_compaction_replaces_the_old_entries(tmp_path):
    s, store = summarizer(tmp_path, FakeLLM(items(("あ" * 50, "あ" * 50)), "- まとめ"),
                          max_chars=40)
    s.summarize(long_session(), DAY)
    assert "あああ" not in store.read()


def test_failed_compaction_keeps_the_memory(tmp_path):
    s, store = summarizer(tmp_path, FakeLLM(items(("あ" * 50, "あ" * 50)), ""), max_chars=40)
    s.summarize(long_session(), DAY)
    assert "あああ" in store.read()


def test_small_memory_is_not_compacted(tmp_path):
    llm = FakeLLM(STRAWBERRY)
    s, _ = summarizer(tmp_path, llm)
    s.summarize(session(), DAY)
    assert len(llm.calls) == 1


def test_evidence_must_come_from_the_user_not_the_character(tmp_path):
    # "おいしいよね" was said by the character; it says nothing about the child.
    s, store = summarizer(tmp_path, FakeLLM(items(("おいしいものがすき", "おいしいよね"))))
    s.summarize(session(), DAY)
    assert store.read() == ""
