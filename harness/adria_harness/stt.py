"""Speech input: microphone -> Silero VAD -> Whisper (MLX), all local.

The listener captures 16 kHz mono audio, uses Silero VAD to find the start and
end of an utterance, and transcribes the utterance with mlx-whisper.
Audio is held in memory only and is never written to disk.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections import deque
from collections.abc import Callable

import numpy as np

from .config import STTConfig

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000
BLOCK = 512  # Silero VAD expects 512-sample windows at 16 kHz
PREROLL_BLOCKS = 10  # ~320 ms of audio kept before the detected speech start

# Whisper tends to hallucinate these on noise/silence; drop them.
_HALLUCINATIONS = (
    "ご視聴ありがとうございました",
    "ご視聴ありがとうございます",
    "チャンネル登録",
    "おやすみなさい。おやすみなさい",
    "字幕",
)


class Transcriber:
    def __init__(self, cfg: STTConfig):
        self.cfg = cfg
        self._lock = threading.Lock()

    def warmup(self) -> None:
        # Loads the model weights; the (silent) result is discarded.
        self._raw(np.zeros(SAMPLE_RATE // 2, dtype=np.float32))

    def _raw(self, audio: np.ndarray) -> dict:
        import mlx_whisper

        with self._lock:
            return mlx_whisper.transcribe(
                audio.astype(np.float32),
                path_or_hf_repo=self.cfg.model,
                language=self.cfg.language,
                condition_on_previous_text=False,
                no_speech_threshold=0.6,
                verbose=None,
            )

    def transcribe(self, audio: np.ndarray) -> str:
        result = self._raw(audio)
        text = (result.get("text") or "").strip()
        if any(h in text for h in _HALLUCINATIONS):
            log.info("dropped likely hallucination: %r", text)
            return ""
        return text


class MicListener:
    """Detects utterances from the default microphone.

    ``is_muted`` is evaluated when each block is *captured* (not when it is
    processed): while the consumer is busy generating or playing a reply, blocks
    keep arriving, and judging them later would let the character hear itself.
    """

    def __init__(self, cfg: STTConfig, is_muted: Callable[[], bool]):
        self.cfg = cfg
        self.is_muted = is_muted
        from silero_vad import VADIterator, load_silero_vad

        # TorchScript model: runs on torch, which silero-vad already depends on
        # (the ONNX variant would need onnxruntime as an extra dependency).
        self._model = load_silero_vad(onnx=False)
        self._vad = VADIterator(
            self._model,
            threshold=cfg.vad_threshold,
            sampling_rate=SAMPLE_RATE,
            min_silence_duration_ms=cfg.min_silence_ms,
            speech_pad_ms=cfg.speech_pad_ms,
        )
        self._blocks: queue.Queue[np.ndarray | None] = queue.Queue()

    def _callback(self, indata, frames, time_info, status):  # sounddevice thread
        if status:
            log.debug("input status: %s", status)
        # None marks a muted block: discard any partial utterance.
        self._blocks.put(None if self.is_muted() else indata[:, 0].copy())

    def utterances(self, stop: threading.Event):
        """Yield (audio, speech_end_monotonic) for each utterance from the microphone."""
        import sounddevice as sd

        def blocks():
            while not stop.is_set():
                try:
                    yield self._blocks.get(timeout=0.1)
                except queue.Empty:
                    continue

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                            blocksize=BLOCK, callback=self._callback):
            yield from self.segment(blocks())

    def segment(self, blocks):
        """Turn a stream of 512-sample blocks (None = muted) into utterances."""
        import torch

        preroll: deque[np.ndarray] = deque(maxlen=PREROLL_BLOCKS)
        speech: list[np.ndarray] | None = None
        max_blocks = int(self.cfg.max_utterance_sec * SAMPLE_RATE / BLOCK)
        for block in blocks:
            if block is None:
                if speech is not None or preroll:
                    speech = None
                    preroll.clear()
                    self._vad.reset_states()
                continue
            event = self._vad(torch.from_numpy(block), return_seconds=False)
            if speech is None:
                preroll.append(block)
                if event and "start" in event:
                    speech = list(preroll)
                    preroll.clear()
                    log.debug("speech start")
                continue
            speech.append(block)
            ended = bool(event and "end" in event)
            if ended or len(speech) >= max_blocks:
                audio = np.concatenate(speech)
                speech = None
                self._vad.reset_states()
                if len(audio) / SAMPLE_RATE >= self.cfg.min_utterance_sec:
                    yield audio, time.monotonic()
