"""Short-term conversation sessions, one persona at a time.

A session is the run of turns with one persona. It ends when the persona
changes (another speaker), after ``idle_sec`` without a turn, or when the
harness exits; an ended session is handed to the summarizer. History is kept
in memory only and never crosses personas: a new persona always starts empty.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Session:
    persona: str
    turns: list[tuple[str, str]] = field(default_factory=list)  # (user, reply)
    last_activity: float = 0.0


class SessionBook:
    def __init__(self, idle_sec: float, clock: Callable[[], float] = time.monotonic):
        self.idle_sec = idle_sec
        self.clock = clock
        self._lock = threading.Lock()
        self._current: Session | None = None

    def begin(self, persona: str) -> Session | None:
        """Make ``persona`` the active one. Returns the session this ended, if any."""
        with self._lock:
            ended = None
            if self._current is not None and self._current.persona != persona:
                ended = self._take()
            if self._current is None:
                self._current = Session(persona, last_activity=self.clock())
            return ended

    def history(self, persona: str, max_turns: int | None = None) -> list[dict]:
        with self._lock:
            if self._current is None or self._current.persona != persona:
                return []
            turns = self._current.turns
            if max_turns is not None:
                turns = turns[-max_turns:]
            messages = []
            for user, reply in turns:
                messages += [{"role": "user", "content": user},
                             {"role": "assistant", "content": reply}]
            return messages

    def record(self, persona: str, user: str, reply: str) -> None:
        with self._lock:
            if self._current is None or self._current.persona != persona:
                self._current = Session(persona)
            self._current.turns.append((user, reply))
            self._current.last_activity = self.clock()

    def end_if_idle(self) -> Session | None:
        with self._lock:
            if self._current is None:
                return None
            if self.clock() - self._current.last_activity < self.idle_sec:
                return None
            return self._take()

    def end(self) -> Session | None:
        with self._lock:
            return self._take()

    def _take(self) -> Session | None:
        ended, self._current = self._current, None
        return ended if ended is not None and ended.turns else None
