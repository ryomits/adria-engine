"""Dialog manager: user text -> Ollama (streamed) -> sentences -> playback queue.

Short-term history is kept in memory only and is never written to disk. The
persona file is re-read on every request and passed as the system prompt, so
it can be edited without restarting anything.
"""

from __future__ import annotations

import logging
import random
import time
import uuid

from .config import Config
from .llm import OllamaClient
from .playqueue import PlayQueue
from .status import Metrics, Status
from .textproc import split_sentences

log = logging.getLogger(__name__)

DEFAULT_EXPRESSION = "neutral"


class Conversation:
    def __init__(self, cfg: Config, llm: OllamaClient, queue: PlayQueue, status: Status,
                 metrics: Metrics):
        self.cfg = cfg
        self.llm = llm
        self.queue = queue
        self.status = status
        self.metrics = metrics
        self.history: list[dict] = []

    def _system_prompt(self) -> str:
        try:
            return self.cfg.persona_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            raise RuntimeError(f"persona file not found: {self.cfg.persona_path}") from None

    def respond(self, user_text: str, turn_id: str | None = None) -> str:
        """Generate a reply and enqueue it line by line. Returns the full reply text."""
        turn_id = turn_id or uuid.uuid4().hex[:8]
        messages = [{"role": "system", "content": self._system_prompt()}]
        messages += self.history[-2 * self.cfg.llm.history_turns:]
        messages.append({"role": "user", "content": user_text})

        self.status.add_thinking(+1)
        t0 = time.monotonic()
        seq = 0
        try:
            if self.cfg.fillers and not self.llm.is_loaded():
                # The model was unloaded while idle and must be reloaded (several
                # seconds). Fill the wait with a short back-channel utterance.
                self._enqueue(turn_id, seq, random.choice(self.cfg.fillers), x_filler=True)
                self.metrics.record("llm_cold", turn_id=turn_id)
                seq += 1
            first_token_at = None
            first_line_recorded = False
            parts: list[str] = []

            def tracked():
                nonlocal first_token_at
                for chunk in self.llm.chat_stream(messages):
                    if first_token_at is None:
                        first_token_at = time.monotonic() - t0
                        self.metrics.record("llm_first_token", turn_id=turn_id,
                                            sec=round(first_token_at, 3))
                    parts.append(chunk)
                    yield chunk

            for sentence in split_sentences(tracked()):
                if not first_line_recorded:
                    first_line_recorded = True
                    self.metrics.record("first_line_enqueued", turn_id=turn_id,
                                        sec=round(time.monotonic() - t0, 3))
                self._enqueue(turn_id, seq, sentence)
                seq += 1
        finally:
            self.status.add_thinking(-1)
        reply = "".join(parts).strip()
        self.metrics.record("llm_done", turn_id=turn_id, sec=round(time.monotonic() - t0, 3),
                            lines=seq)
        self.history += [{"role": "user", "content": user_text},
                         {"role": "assistant", "content": reply}]
        return reply

    def _enqueue(self, turn_id: str, seq: int, text: str, **x) -> None:
        item = {
            "id": f"{turn_id}-{seq}",
            "turn_id": turn_id,
            "seq": seq,
            "text": text,
            # Display hints. Replies carry no expression markup yet, so use a default.
            "x_expression": DEFAULT_EXPRESSION,
            **x,
        }
        self.queue.push(item)
