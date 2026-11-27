"""Signals for the display app: ``now_playing`` and ``state`` files.

``now_playing`` holds the line currently being played (including ``x_`` keys,
which the display app uses for expressions), or ``{"playing": false}``.

``state`` holds the conversation state shown by the display:

- ``idle``: standby; the microphone is closed
- ``listening``: a conversation is on and the microphone is open
- ``thinking``: a reply is being generated or synthesized
- ``speaking``: a reply is being played

Both files are written atomically.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from .fileio import write_json_atomic


class Status:
    def __init__(self, runtime_dir: Path):
        self.now_playing_path = runtime_dir / "now_playing"
        self.state_path = runtime_dir / "state"
        self._lock = threading.Lock()
        self.active = False  # a conversation is on (started by a click on the display)
        self.thinking = 0  # number of in-flight LLM generations
        self.speaking = False
        # Reply lines are queued or being synthesized but no sound has started yet.
        self.preparing = False
        self._state: str | None = None
        self.set_now_playing(None)
        self._publish()

    def set_now_playing(self, item: dict | None, **extra) -> None:
        if item is None:
            payload = {"playing": False, "updated_at": time.time()}
        else:
            payload = {"playing": True, **item, **extra, "updated_at": time.time()}
        write_json_atomic(self.now_playing_path, payload)

    def update(self, **kw) -> None:
        with self._lock:
            for k, v in kw.items():
                setattr(self, k, v)
            self._publish()

    def add_thinking(self, delta: int) -> None:
        with self._lock:
            self.thinking = max(0, self.thinking + delta)
            self._publish()

    def _compute(self) -> str:
        if self.speaking:
            return "speaking"
        if self.thinking or self.preparing:
            return "thinking"
        if self.active:
            return "listening"
        return "idle"

    def _publish(self) -> None:
        state = self._compute()
        if state != self._state:
            self._state = state
            write_json_atomic(self.state_path, {"state": state, "since": time.time()})

    @property
    def state(self) -> str:
        return self._state or "idle"


class Metrics:
    """Latency metrics (timestamps only, never conversation text)."""

    def __init__(self, runtime_dir: Path):
        self.path = runtime_dir / "metrics.jsonl"
        self._lock = threading.Lock()

    def record(self, event: str, **fields) -> None:
        line = json.dumps({"t": time.time(), "event": event, **fields}, ensure_ascii=False)
        with self._lock, self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
