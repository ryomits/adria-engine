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
import logging
from collections.abc import Callable
from pathlib import Path

from .fileio import write_atomic
from .persona import Persona, check_name
from .sessions import Session

log = logging.getLogger(__name__)

ASSISTANT_LABEL = "キャラクター"
NOTHING = {"なし", "特になし", "- なし", "・なし"}

MEMORY_HEADER = (
    "# これまでのおはなしのメモ\n"
    "前の会話の要約です。話題を広げるのに自然に使ってください。"
    "メモにないことを覚えているふりはしないでください。"
)

SUMMARY_SYSTEM = (
    "あなたは会話の記録係です。次の会話から、次回の会話で役に立つことだけを、"
    "日本語の短い箇条書き（各行「- 」で始める）で書いてください。\n"
    "観点: {focus}\n"
    "会話に出てこないことは書かないでください。推測もしないでください。"
    "残すことがなければ「なし」とだけ書いてください。"
)

COMPACT_SYSTEM = (
    "あなたは会話の記録係です。次のメモを整理して、{max_chars}文字以内の"
    "日本語の箇条書き（各行「- 」で始める）にまとめ直してください。\n"
    "観点: {focus}\n"
    "重複はまとめ、食い違う内容は日付の新しい方を残してください。"
    "メモにないことは書かないでください。"
)


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


ChatFn = Callable[[list[dict]], str]


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
        summary = self.chat([
            {"role": "system", "content": SUMMARY_SYSTEM.format(focus=focus)},
            {"role": "user", "content": transcript},
        ]).strip()
        if not summary or summary in NOTHING:
            log.info("session with %s: nothing to remember", persona.name)
            return
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
