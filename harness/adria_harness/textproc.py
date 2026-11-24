"""Text helpers: split streaming LLM output into speakable lines."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator

_TERMINATORS = "。！？!?\n"
# Closing brackets/quotes that belong to the sentence just ended.
_TRAILING = "」』）)〜～ー…"
_MIN_CHARS = 2

# Characters that should not be read aloud (markdown, emoji, decoration).
_STRIP_RE = re.compile(
    r"[*#`_>|\[\]{}]"
    r"|[\U0001F000-\U0001FAFF☀-➿️‍]"
)


def clean_for_speech(text: str) -> str:
    text = _STRIP_RE.sub("", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(chunks: Iterable[str]) -> Iterator[str]:
    """Yield complete sentences as soon as they are available in the stream.

    Fragments shorter than ``_MIN_CHARS`` (e.g. a lone "！") are merged into
    the following sentence instead of being spoken on their own.
    """
    buf = ""
    for chunk in chunks:
        buf += chunk
        while True:
            idx = _find_boundary(buf)
            if idx < 0:
                break
            sentence, buf = clean_for_speech(buf[:idx]), buf[idx:]
            if sentence:
                yield sentence
    tail = clean_for_speech(buf)
    if tail:
        yield tail


def _find_boundary(buf: str) -> int:
    """Index just past the first sentence end that leaves a long-enough sentence."""
    i = 0
    while i < len(buf):
        if buf[i] in _TERMINATORS:
            j = i + 1
            # absorb runs like "！？" or "。」"
            while j < len(buf) and (buf[j] in _TERMINATORS or buf[j] in _TRAILING):
                j += 1
            if j == len(buf):
                # more trailing characters may still arrive
                return -1
            if len(clean_for_speech(buf[:j])) >= _MIN_CHARS:
                return j
            i = j
            continue
        i += 1
    return -1


def limit_reply(sentences: Iterator[str], max_sentences: int, max_chars: int) -> Iterator[str]:
    """Pass sentences through until the persona's reply length limit is reached.

    The first sentence is always kept whole. Nothing is read from ``sentences``
    after the cut, so closing the stream stops the LLM generation early.
    """
    total = 0
    for count, sentence in enumerate(sentences, start=1):
        if count > 1 and total + len(sentence) > max_chars:
            return
        total += len(sentence)
        yield sentence
        if count >= max_sentences:
            return
