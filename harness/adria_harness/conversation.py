"""Dialog manager: user text -> Ollama (streamed) -> sentences -> playback queue.

The persona file is re-read for every request and passed as the system
prompt together with the long-term memory. Short-term history lives in the
session in memory only; the full transcript is written to a write-only log for
parents and never read back.
"""

from __future__ import annotations

import logging
import random
import time
import uuid

from .config import Config
from .llm import OllamaClient
from .memory import MemoryStore, build_system_prompt
from .persona import load_persona
from .playqueue import PlayQueue
from .sessions import SessionBook
from .status import Metrics, Status
from .textproc import limit_reply, split_sentences
from .transcript import TranscriptLog

log = logging.getLogger(__name__)

DEFAULT_EXPRESSION = "neutral"


class Conversation:
    def __init__(self, cfg: Config, llm: OllamaClient, queue: PlayQueue, status: Status,
                 metrics: Metrics, sessions: SessionBook, memory: MemoryStore,
                 transcript: TranscriptLog):
        self.cfg = cfg
        self.llm = llm
        self.queue = queue
        self.status = status
        self.metrics = metrics
        self.sessions = sessions
        self.memory = memory
        self.transcript = transcript

    def respond(self, user_text: str, turn_id: str | None = None) -> str:
        """Generate a reply and enqueue it line by line. Returns the text that was queued."""
        turn_id = turn_id or uuid.uuid4().hex[:8]
        persona = load_persona(self.cfg.persona_path)
        system = build_system_prompt(persona, self.memory.read())
        messages = [{"role": "system", "content": system}]
        messages += self.sessions.history(max_turns=self.cfg.llm.history_turns)
        messages.append({"role": "user", "content": user_text})

        self.status.add_thinking(+1)
        t0 = time.monotonic()
        seq = 0
        spoken: list[str] = []
        try:
            if self.cfg.fillers and not self.llm.is_loaded():
                # The model was unloaded while idle and must be reloaded (several
                # seconds). Fill the wait with a short back-channel utterance.
                self._enqueue(turn_id, seq, random.choice(self.cfg.fillers), x_filler=True)
                self.metrics.record("llm_cold", turn_id=turn_id)
                seq += 1
            first_token_at = None

            def tracked():
                nonlocal first_token_at
                for chunk in self.llm.chat_stream(messages):
                    if first_token_at is None:
                        first_token_at = time.monotonic() - t0
                        self.metrics.record("llm_first_token", turn_id=turn_id,
                                            sec=round(first_token_at, 3))
                    yield chunk

            stream = tracked()
            sentences = split_sentences(stream)
            try:
                for sentence in limit_reply(sentences, persona.reply.max_sentences,
                                            persona.reply.max_chars):
                    if not spoken:
                        self.metrics.record("first_line_enqueued", turn_id=turn_id,
                                            sec=round(time.monotonic() - t0, 3))
                    self._enqueue(turn_id, seq, sentence)
                    spoken.append(sentence)
                    seq += 1
            finally:
                # Past the length limit: close the HTTP stream so Ollama stops generating.
                sentences.close()
                stream.close()
        finally:
            self.status.add_thinking(-1)
        reply = "".join(spoken)
        self.metrics.record("llm_done", turn_id=turn_id, sec=round(time.monotonic() - t0, 3),
                            lines=seq)
        self.sessions.record(user_text, reply)
        self.transcript.append({
            "turn_id": turn_id,
            "user": user_text,
            "reply": reply,
        })
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
