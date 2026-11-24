"""Dialog manager: user text -> Ollama (streamed) -> sentences -> playback queue.

The harness, not the LLM, decides who it is talking as: each request names a
persona (chosen from the speaker), whose file is re-read every time and passed
as the system prompt together with that persona's memory. Short-term history
lives in a per-persona session in memory only; the full transcript is written
to a write-only log for parents and never read back.
"""

from __future__ import annotations

import logging
import random
import time
import uuid
from collections.abc import Callable

from .config import Config
from .llm import OllamaClient
from .memory import MemoryStore, build_system_prompt
from .persona import Persona, load_persona
from .playqueue import PlayQueue
from .sessions import Session, SessionBook
from .speaker import SpeakerMatch
from .status import Metrics, Status
from .textproc import limit_reply, split_sentences
from .transcript import TranscriptLog

log = logging.getLogger(__name__)

DEFAULT_EXPRESSION = "neutral"


class Conversation:
    def __init__(self, cfg: Config, llm: OllamaClient, queue: PlayQueue, status: Status,
                 metrics: Metrics, sessions: SessionBook, memory: MemoryStore,
                 transcript: TranscriptLog, on_session_end: Callable[[Session], None]):
        self.cfg = cfg
        self.llm = llm
        self.queue = queue
        self.status = status
        self.metrics = metrics
        self.sessions = sessions
        self.memory = memory
        self.transcript = transcript
        self.on_session_end = on_session_end

    def persona(self, name: str) -> Persona:
        return load_persona(self.cfg.persona_dir, name)

    def respond(self, user_text: str, persona_name: str | None = None,
                speaker: SpeakerMatch | None = None, turn_id: str | None = None) -> str:
        """Generate a reply and enqueue it line by line. Returns the text that was queued."""
        turn_id = turn_id or uuid.uuid4().hex[:8]
        persona = self.persona(persona_name or self.cfg.default_persona)
        ended = self.sessions.begin(persona.name)
        if ended is not None:
            self.on_session_end(ended)
        system = build_system_prompt(persona, self.memory.read(persona.name))
        messages = [{"role": "system", "content": system}]
        messages += self.sessions.history(persona.name, max_turns=self.cfg.llm.history_turns)
        messages.append({"role": "user", "content": user_text})

        self.status.add_thinking(+1)
        t0 = time.monotonic()
        seq = 0
        spoken: list[str] = []
        try:
            if self.cfg.fillers and not self.llm.is_loaded():
                # The model was unloaded while idle and must be reloaded (several
                # seconds). Fill the wait with a short back-channel utterance.
                self._enqueue(turn_id, seq, random.choice(self.cfg.fillers), persona,
                              x_filler=True)
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
                    self._enqueue(turn_id, seq, sentence, persona)
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
                            lines=seq, persona=persona.name)
        self.sessions.record(persona.name, user_text, reply)
        self.transcript.append({
            "turn_id": turn_id,
            "persona": persona.name,
            "speaker": None if speaker is None else speaker.speaker,
            "speaker_score": None if speaker is None else round(speaker.score, 3),
            "user": user_text,
            "reply": reply,
        })
        return reply

    def _enqueue(self, turn_id: str, seq: int, text: str, persona: Persona, **x) -> None:
        item = {
            "id": f"{turn_id}-{seq}",
            "turn_id": turn_id,
            "seq": seq,
            "text": text,
            # Display hints. Replies carry no expression markup yet, so use a default.
            "x_expression": DEFAULT_EXPRESSION,
            **x,
        }
        # Persona voice settings for the TTS layer (omitted: global settings).
        if persona.voice.reference is not None:
            item["voice"] = persona.voice.reference
        if persona.voice.caption is not None:
            item["caption"] = persona.voice.caption
        self.queue.push(item)
