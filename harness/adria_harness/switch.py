"""Conversation on/off.

A conversation starts with a click on the display and ends with another click
or after ``timeout_sec`` without speech. In standby the microphone is closed.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class ConversationSwitch:
    def __init__(self, timeout_sec: float, clock: Callable[[], float] = time.monotonic,
                 on_change: Callable[[bool], None] = lambda active: None):
        self.timeout_sec = timeout_sec
        self.clock = clock
        self.on_change = on_change
        self._lock = threading.Lock()
        self._active = threading.Event()
        self._standby = threading.Event()
        self._standby.set()
        self._last_activity = 0.0

    @property
    def active(self) -> bool:
        return self._active.is_set()

    def toggle(self) -> bool:
        """Start a conversation in standby, or end the running one. Returns the new state."""
        with self._lock:
            self._set(not self._active.is_set())
            return self.active

    def stop(self) -> None:
        with self._lock:
            self._set(False)

    def touch(self) -> None:
        """Someone spoke or a reply was given: restart the silence timeout."""
        with self._lock:
            self._last_activity = self.clock()

    def expire(self) -> bool:
        """Go to standby after the silence timeout. Returns True if this ended it."""
        with self._lock:
            if not self._active.is_set():
                return False
            if self.clock() - self._last_activity < self.timeout_sec:
                return False
            self._set(False)
            return True

    def wait_active(self, timeout: float | None = None) -> bool:
        return self._active.wait(timeout)

    def standby_signal(self) -> threading.Event:
        """An event that is set while in standby (to stop the microphone loop)."""
        return self._standby

    def _set(self, active: bool) -> None:
        if active == self._active.is_set():
            return
        if active:
            self._last_activity = self.clock()
            self._standby.clear()
            self._active.set()
        else:
            self._active.clear()
            self._standby.set()
        self.on_change(active)
