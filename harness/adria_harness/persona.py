"""The persona file: Markdown with an optional TOML front matter.

    +++
    [reply]
    max_sentences = 3        # the harness stops speaking after this many sentences
    max_chars = 120          # ... or once this many characters have been spoken
    [memory]
    user_label = "子ども"     # how the other speaker is named in summaries
    focus = ["...", "..."]   # what the session summary should keep
    +++
    (Markdown body: personality, safety rules, example conversations)

There is one persona, ``ADRIA_HOME/persona.md``. The body is passed to the LLM
as the system prompt. The file is read again for every request, so editing it
changes the next reply without a restart.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

FENCE = "+++"

DEFAULT_FOCUS = (
    "すきなもの・きらいなもの",
    "保育園の友達の名前",
    "続いている ごっこ遊び の設定",
    "約束したこと",
)


class PersonaError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReplyLimits:
    max_sentences: int = 3
    max_chars: int = 120


@dataclass(frozen=True)
class MemorySpec:
    user_label: str = "ユーザー"
    focus: tuple[str, ...] = DEFAULT_FOCUS


@dataclass(frozen=True)
class Persona:
    prompt: str
    reply: ReplyLimits = field(default_factory=ReplyLimits)
    memory: MemorySpec = field(default_factory=MemorySpec)


def _split_front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith(FENCE + "\n"):
        return {}, text
    end = text.find("\n" + FENCE + "\n", len(FENCE))
    if end < 0:
        raise PersonaError("front matter is not closed with +++")
    head = text[len(FENCE) + 1:end + 1]
    body = text[end + len(FENCE) + 2:]
    try:
        return tomllib.loads(head), body
    except tomllib.TOMLDecodeError as e:
        raise PersonaError(f"front matter: {e}") from e


def _section(data: dict, key: str, allowed: set[str]) -> dict:
    values = data.get(key, {})
    if not isinstance(values, dict):
        raise PersonaError(f"[{key}] must be a table")
    unknown = set(values) - allowed
    if unknown:
        raise PersonaError(f"unknown key(s) in [{key}]: {', '.join(sorted(unknown))}")
    return values


def _positive_int(values: dict, key: str, default: int) -> int:
    value = values.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise PersonaError(f"{key} must be a positive integer")
    return value


def parse_persona(text: str) -> Persona:
    data, body = _split_front_matter(text)
    unknown = set(data) - {"reply", "memory"}
    if unknown:
        raise PersonaError(f"unknown section(s): {', '.join(sorted(unknown))} "
                           "(the voice is set in config.toml [tts])")
    reply = _section(data, "reply", {"max_sentences", "max_chars"})
    memory = _section(data, "memory", {"user_label", "focus"})
    prompt = body.strip()
    if not prompt:
        raise PersonaError("the persona has no prompt text")
    focus = memory.get("focus", list(DEFAULT_FOCUS))
    if not isinstance(focus, list) or not all(isinstance(f, str) for f in focus):
        raise PersonaError("memory.focus must be a list of strings")
    user_label = memory.get("user_label", MemorySpec.user_label)
    if not isinstance(user_label, str) or not user_label:
        raise PersonaError("memory.user_label must be a non-empty string")
    defaults = ReplyLimits()
    return Persona(
        prompt=prompt,
        reply=ReplyLimits(
            max_sentences=_positive_int(reply, "max_sentences", defaults.max_sentences),
            max_chars=_positive_int(reply, "max_chars", defaults.max_chars),
        ),
        memory=MemorySpec(user_label=user_label, focus=tuple(focus)),
    )


def load_persona(path: Path) -> Persona:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise PersonaError(f"persona file not found: {path}") from None
    try:
        return parse_persona(text)
    except PersonaError as e:
        raise PersonaError(f"{path}: {e}") from None
