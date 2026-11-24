"""Background summarization of ended sessions.

Summaries use the same local LLM as the conversation, and Ollama runs one
request at a time, so a summary is started only while nobody is talking
(``may_run``). At exit, ``drain`` summarizes whatever is still pending.
"""

from __future__ import annotations

import datetime as dt
import logging
import queue
import threading
import time
from collections.abc import Callable
from typing import Protocol

from .sessions import Session

log = logging.getLogger(__name__)


class SessionSummarizer(Protocol):
    def summarize(self, session: Session, day: dt.date) -> None: ...


class SummaryWorker:
    def __init__(self, summarizer: SessionSummarizer, may_run: Callable[[], bool],
                 poll_sec: float = 0.5):
        self.summarizer = summarizer
        self.may_run = may_run
        self.poll_sec = poll_sec
        self._jobs: queue.Queue[Session] = queue.Queue()
        self._draining = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="summary")

    def start(self) -> None:
        self._thread.start()

    def submit(self, session: Session) -> None:
        log.info("session with %s ended (%d turns); summary queued", session.persona,
                 len(session.turns))
        self._jobs.put(session)

    def drain(self, timeout: float) -> bool:
        """Summarize everything pending now. Returns False if it did not finish in time."""
        self._draining.set()
        deadline = time.monotonic() + timeout
        while self._jobs.unfinished_tasks:
            if time.monotonic() > deadline:
                log.warning("%d session summary(ies) not saved before exit",
                            self._jobs.unfinished_tasks)
                return False
            time.sleep(0.02)
        return True

    def _run(self) -> None:
        while True:
            session = self._jobs.get()
            try:
                while not (self._draining.is_set() or self.may_run()):
                    time.sleep(self.poll_sec)
                self.summarizer.summarize(session, dt.date.today())
            except Exception:
                log.exception("session summary for %s failed", session.persona)
            finally:
                self._jobs.task_done()
