"""Long-term memory: per-persona session summaries.

- When a session ends, the LLM summarizes it and the summary is appended to
  ``memory/<persona>.md`` in the private home. Only summaries are kept; no
  audio and no full transcript ever enter this file.
- When a file grows beyond ``max_chars``, the LLM merges it into one shorter
  summary.
- At the start of each request the persona's file is added to its system
  prompt. Files are keyed by persona name, so personas never share memories.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import re
from collections.abc import Callable
from pathlib import Path

from .fileio import write_atomic
from .persona import Persona, check_name
from .sessions import Session

log = logging.getLogger(__name__)

ASSISTANT_LABEL = "キャラクター"
# Evidence shorter than this (after normalization) proves nothing.
MIN_EVIDENCE_CHARS = 4
_IGNORED_IN_MATCH = re.compile(r"[\s、。，．,.!！?？「」『』（）()〜～ー…・]")

MEMORY_HEADER = (
    "# これまでのおはなしのメモ\n"
    "前の会話の要約です。話題を広げるのに自然に使ってください。"
    "メモにないことを覚えているふりはしないでください。"
)

SUMMARY_SYSTEM = (
    "あなたは会話の記録係です。次の会話から、次回の会話で役に立つことだけを取り出してください。\n"
    "観点: {focus}\n"
    "観点に当てはまる発言が会話になければ、その観点は書かないでください。推測や想像は禁止です。\n"
    "memo は「{user}は〜」のように第三者の立場で短く書き、evidence には根拠になった"
    "{user}の発言をそのまま一字一句写してください。\n"
    '出力は JSON のみ: {{"items": [{{"memo": "...", "evidence": "..."}}]}}\n'
    '残すことがなければ {{"items": []}} を出力してください。'
)

COMPACT_SYSTEM = (
    "あなたは会話の記録係です。次のメモを整理して、{max_chars}文字以内の"
    "日本語の箇条書き（各行「- 」で始める）にまとめ直してください。\n"
    "観点: {focus}\n"
    "重複はまとめ、食い違う内容は日付の新しい方を残してください。"
    "メモにないことは書かないでください。"
)


def _normalize(text: str) -> str:
    return _IGNORED_IN_MATCH.sub("", text)


def grounded_memos(reply: str, user_said: list[str]) -> list[str]:
    """Memos from the LLM's JSON reply whose quoted evidence the user really said.

    Small models fill every requested topic, inventing names and games that
    were never mentioned. Each memo must quote what was said; memos whose quote
    cannot be found in the user's own utterances are dropped (what the
    character said is no evidence about the user).
    """
    try:
        items = json.loads(reply).get("items", [])
    except (ValueError, AttributeError):
        log.warning("session summary was not valid JSON; nothing saved")
        return []
    said = [_normalize(u) for u in user_said]
    memos = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        memo, evidence = item.get("memo"), item.get("evidence")
        if not isinstance(memo, str) or not isinstance(evidence, str) or not memo.strip():
            continue
        quote = _normalize(evidence)
        if len(quote) >= MIN_EVIDENCE_CHARS and any(quote in u for u in said):
            memos.append(memo.strip())
        else:
            log.info("dropped a memo without evidence in the conversation: %r", memo)
    return memos


class MemoryStore:
    def __init__(self, memory_dir: Path):
        self.dir = memory_dir

    def path(self, persona: str) -> Path:
        return self.dir / f"{check_name(persona)}.md"

    def read(self, persona: str) -> str:
        try:
            return self.path(persona).read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return ""

    def append(self, persona: str, day: dt.date, summary: str) -> None:
        current = self.read(persona)
        entry = f"## {day.isoformat()}\n{summary.strip()}"
        self.replace(persona, f"{current}\n\n{entry}" if current else entry)

    def replace(self, persona: str, text: str) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        write_atomic(self.path(persona), text.strip() + "\n")


def build_system_prompt(persona: Persona, memory: str) -> str:
    if not memory:
        return persona.prompt
    return f"{persona.prompt}\n\n{MEMORY_HEADER}\n\n{memory}"


ChatFn = Callable[..., str]  # (messages, json_output=False) -> reply text


class Summarizer:
    def __init__(self, chat: ChatFn, store: MemoryStore, max_chars: int,
                 personas: Callable[[str], Persona]):
        self.chat = chat
        self.store = store
        self.max_chars = max_chars
        self.personas = personas

    def summarize(self, session: Session, day: dt.date) -> None:
        persona = self.personas(session.persona)
        focus = "、".join(persona.memory.focus)
        transcript = "\n".join(
            f"{persona.memory.user_label}: {user}\n{ASSISTANT_LABEL}: {reply}"
            for user, reply in session.turns)
        reply = self.chat([
            {"role": "system", "content": SUMMARY_SYSTEM.format(
                focus=focus, user=persona.memory.user_label)},
            {"role": "user", "content": transcript},
        ], json_output=True)
        memos = grounded_memos(reply, [user for user, _ in session.turns])
        if not memos:
            log.info("session with %s: nothing to remember", persona.name)
            return
        summary = "\n".join(f"- {m}" for m in memos)
        self.store.append(persona.name, day, summary)
        log.info("saved a session summary for %s (%d chars)", persona.name, len(summary))
        self._compact_if_needed(persona, focus, day)

    def _compact_if_needed(self, persona: Persona, focus: str, day: dt.date) -> None:
        memory = self.store.read(persona.name)
        if len(memory) <= self.max_chars:
            return
        merged = self.chat([
            {"role": "system",
             "content": COMPACT_SYSTEM.format(max_chars=self.max_chars, focus=focus)},
            {"role": "user", "content": memory},
        ]).strip()
        if not merged or len(merged) >= len(memory):
            # Never lose memories to a bad merge; try again after the next session.
            log.warning("memory compaction for %s gave no shorter result; kept as is",
                        persona.name)
            return
        self.store.replace(persona.name, f"## {day.isoformat()} までのまとめ\n{merged}")
        log.info("compacted memory for %s: %d -> %d chars", persona.name, len(memory),
                 len(merged))
