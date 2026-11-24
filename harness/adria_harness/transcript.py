"""Full conversation log for parents to look back on.

One JSON line per turn in ``<dir>/YYYY-MM-DD.jsonl`` (owner-only permissions).
Files older than the retention period are deleted on startup and whenever a
turn is written.

This log is write-only from the harness: nothing reads it back, so it can never
reach the LLM context. Long-term memory comes only from the session summaries.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import threading
from pathlib import Path

log = logging.getLogger(__name__)

FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.jsonl$")


class TranscriptLog:
    def __init__(self, log_dir: Path, retention_days: int):
        self._dir = log_dir
        self._retention = dt.timedelta(days=retention_days)
        self._lock = threading.Lock()

    def append(self, entry: dict, now: dt.datetime | None = None) -> None:
        now = now or dt.datetime.now()
        record = {"at": now.isoformat(timespec="seconds"), **entry}
        with self._lock:
            self._dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            path = self._dir / f"{now.date().isoformat()}.jsonl"
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self.purge(now)

    def purge(self, now: dt.datetime | None = None) -> None:
        """Delete day files older than the retention period."""
        today = (now or dt.datetime.now()).date()
        if not self._dir.is_dir():
            return
        for path in self._dir.iterdir():
            m = FILE_RE.match(path.name)
            if not m:
                continue
            try:
                day = dt.date.fromisoformat(m.group(1))
            except ValueError:
                continue
            if today - day >= self._retention:
                path.unlink(missing_ok=True)
                log.info("deleted expired transcript %s", path.name)
