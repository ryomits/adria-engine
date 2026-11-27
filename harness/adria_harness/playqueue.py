"""File-based playback queue: one JSON object per line.

Format of each line (dialog item)::

    {"id": "...", "turn_id": "...", "seq": 0, "text": "...", "x_expression": "neutral"}

Keys prefixed with ``x_`` carry display-side hints (expression etc.). They are
stripped before anything is sent to the TTS server (see ``tts_fields``).

Concurrency:
- Writers/consumers serialize on an ``flock`` of ``queue.lock`` so multiple
  processes can share the queue safely.
- The queue file itself is always replaced atomically (``.part`` + rename), so
  lock-free readers never see a partial line.
"""

from __future__ import annotations

import fcntl
import json
from contextlib import contextmanager
from pathlib import Path

from .fileio import write_atomic


def tts_fields(item: dict) -> dict:
    """Return the item without ``x_`` keys (what the TTS side is allowed to see)."""
    return {k: v for k, v in item.items() if not k.startswith("x_")}


class PlayQueue:
    def __init__(self, runtime_dir: Path):
        self.path = runtime_dir / "queue.jsonl"
        self.lock_path = runtime_dir / "queue.lock"
        self.lock_path.touch(exist_ok=True)

    @contextmanager
    def _locked(self):
        with self.lock_path.open("r") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)

    def _read(self) -> list[dict]:
        try:
            text = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def _write(self, items: list[dict]) -> None:
        body = "".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items)
        write_atomic(self.path, body)

    def push(self, *items: dict) -> None:
        with self._locked():
            current = self._read()
            current.extend(items)
            self._write(current)

    def pop(self) -> dict | None:
        with self._locked():
            current = self._read()
            if not current:
                return None
            head, rest = current[0], current[1:]
            self._write(rest)
            return head

    def __len__(self) -> int:
        return len(self._read())

    def clear(self) -> None:
        with self._locked():
            self._write([])
