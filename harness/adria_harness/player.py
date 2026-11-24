"""Playback loop: queue -> Irodori-TTS -> speakers, with look-ahead synthesis.

While line N is playing, lines N+1.. are already being synthesized on a worker
thread, so the gap between lines is only the time left over (if any) after
playback of N ends.
"""

from __future__ import annotations

import io
import logging
import threading
import time
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor

import numpy as np
import soundfile as sf

from .lipsync import mouth_curve
from .playqueue import PlayQueue, tts_fields
from .status import Metrics, Status
from .tts import IrodoriTTS

log = logging.getLogger(__name__)

LOOKAHEAD = 2  # number of lines synthesized ahead of the one playing


class Player:
    def __init__(self, queue: PlayQueue, tts: IrodoriTTS, status: Status, metrics: Metrics,
                 mute: bool = False):
        self.queue = queue
        self.tts = tts
        self.status = status
        self.metrics = metrics
        self.mute = mute  # for automated tests: time playback without sound output
        self._mute_end = 0.0
        self._exec = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tts-synth")
        self._pending: deque[tuple[dict, Future]] = deque()
        # Guards the hand-over from the queue file to ``_pending`` so that
        # ``wait_idle`` never sees an item that is in neither place.
        self._handover = threading.Lock()
        self._stop = threading.Event()
        self._idle = threading.Event()
        self._idle.set()
        self.last_playback_end = 0.0
        self.first_play_at: dict[str, float] = {}  # turn_id -> monotonic time of first audio
        self._thread = threading.Thread(target=self._run, daemon=True, name="player")

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)
        self._exec.shutdown(wait=False, cancel_futures=True)

    def wait_idle(self, timeout: float | None = None) -> bool:
        """Block until the queue is drained and nothing is playing."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with self._handover:
                if self._idle.is_set() and len(self.queue) == 0 and not self._pending:
                    return True
            if deadline is not None and time.monotonic() > deadline:
                return False
            time.sleep(0.05)

    # ---------- internals ----------

    def _synth(self, item: dict) -> tuple[np.ndarray, int, float]:
        text = tts_fields(item)["text"]
        t0 = time.monotonic()
        wav = self.tts.synthesize(text)
        data, sr = sf.read(io.BytesIO(wav), dtype="float32")
        return data, sr, time.monotonic() - t0

    def _fill(self) -> None:
        with self._handover:
            while len(self._pending) < LOOKAHEAD:
                item = self.queue.pop()
                if item is None:
                    return
                self._pending.append((item, self._exec.submit(self._synth, item)))

    def _run(self) -> None:
        while not self._stop.is_set():
            self._fill()
            if not self._pending:
                if not self._idle.is_set():
                    # Keep "speaking" across the short gaps between lines; drop
                    # it only once everything queued has been played.
                    self.status.update(speaking=False)
                self._idle.set()
                time.sleep(0.03)
                continue
            with self._handover:
                self._idle.clear()
                item, fut = self._pending.popleft()
            wait_t0 = time.monotonic()
            try:
                data, sr, synth_sec = fut.result()
            except Exception:
                log.exception("synthesis failed; skipping line")
                continue
            gap = time.monotonic() - wait_t0  # time spent waiting on synthesis
            self._play(item, data, sr, synth_sec, gap)

    def _start_output(self, data: np.ndarray, sr: int) -> float:
        """Start playback; return the output latency (time until the sound is heard)."""
        if self.mute:
            return 0.0
        import sounddevice as sd

        sd.play(data, sr)
        return float(sd.get_stream().latency)

    def _playing(self) -> bool:
        if self.mute:
            return time.monotonic() < self._mute_end
        import sounddevice as sd

        return sd.get_stream().active

    def _play(self, item: dict, data: np.ndarray, sr: int, synth_sec: float, gap: float) -> None:
        duration = len(data) / sr
        mouth = mouth_curve(data, sr).to_json()
        self._mute_end = time.monotonic() + duration
        latency = self._start_output(data, sr)
        # The display samples the mouth curve by wall-clock time, so start it when
        # the sound actually comes out (Bluetooth output can lag by 100+ ms).
        started = time.time() + latency
        self.first_play_at.setdefault(item.get("turn_id"), time.monotonic())
        self.status.set_now_playing(item, started_at=started, duration=duration, mouth=mouth)
        self.status.update(speaking=True)
        self.metrics.record("play_start", turn_id=item.get("turn_id"), seq=item.get("seq"),
                            synth_sec=round(synth_sec, 3), wait_sec=round(gap, 3),
                            duration=round(duration, 3), chars=len(item.get("text", "")),
                            output_latency=round(latency, 3))
        log.info("play [%s#%s] %.2fs (synth %.2fs, waited %.2fs, output latency %.0f ms)",
                 item.get("turn_id"), item.get("seq"), duration, synth_sec, gap, latency * 1000)
        while self._playing() and not self._stop.is_set():
            self._fill()  # keep the look-ahead synthesis busy during playback
            time.sleep(0.02)
        if not self.mute:
            import sounddevice as sd

            sd.stop()
        self.last_playback_end = time.monotonic()
        self.status.set_now_playing(None)
