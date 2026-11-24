"""Atomic file helpers shared by the queue, now_playing and state files.

Readers (including the display app) must never observe a half-written file, so
every write goes to ``<name>.part`` first and is then renamed into place.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def write_atomic(path: Path, text: str) -> None:
    part = path.with_name(path.name + ".part")
    with part.open("w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(part, path)


def write_json_atomic(path: Path, obj) -> None:
    write_atomic(path, json.dumps(obj, ensure_ascii=False) + "\n")
