"""Irodori-TTS client with an on-demand server lifecycle.

- The server is started lazily on the first synthesis request.
- It is stopped after ``idle_stop_sec`` without synthesis (default 30 min),
  freeing its memory; the next request starts it again.
- The server binds to loopback only and runs with Hugging Face offline mode,
  so nothing leaves this Mac at runtime.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from .config import TTSConfig

log = logging.getLogger(__name__)


class TTSError(RuntimeError):
    pass


class IrodoriTTS:
    def __init__(self, cfg: TTSConfig, voices_dir: Path, log_dir: Path):
        self.cfg = cfg
        self.voices_dir = voices_dir
        self.log_dir = log_dir
        self._proc: subprocess.Popen | None = None
        self._lock = threading.RLock()
        self._last_used = time.monotonic()
        self._stop_evt = threading.Event()
        self._watcher = threading.Thread(target=self._idle_watch, daemon=True, name="tts-idle")
        self._watcher.start()
        self.last_start_sec: float | None = None  # time it took to bring the server up

    # ---------- server lifecycle ----------

    def health(self) -> dict | None:
        try:
            with urllib.request.urlopen(self.cfg.base_url + "/health", timeout=2) as r:
                return json.load(r)
        except (OSError, ValueError):
            return None

    def is_ready(self) -> bool:
        h = self.health()
        return bool(h and h.get("runtime", {}).get("loaded"))

    def ensure_running(self) -> None:
        with self._lock:
            if self.is_ready():
                return
            spawned = False
            if self.health() is None and (self._proc is None or self._proc.poll() is not None):
                self._spawn()
                spawned = True
            self._wait_ready()
            if spawned:
                self._warmup()

    def _warmup(self) -> None:
        # The first synthesis after a (re)start is several times slower on MPS
        # (kernel compilation). Pay that cost here instead of on a real reply.
        t0 = time.monotonic()
        try:
            self._request("あ。")
        except TTSError:
            log.warning("TTS warmup failed", exc_info=True)
        log.info("TTS warmup took %.1fs", time.monotonic() - t0)

    def prestart(self) -> None:
        """Start (and warm up) the server in the background."""
        def run():
            try:
                self.ensure_running()
                self._last_used = time.monotonic()
            except TTSError:
                log.exception("TTS prestart failed")

        threading.Thread(target=run, daemon=True, name="tts-prestart").start()

    def _server_env(self) -> dict:
        env = dict(os.environ)
        env.update({
            # Runtime must work fully offline; models are fetched only by setup.
            "HF_HUB_OFFLINE": "0" if env.get("ADRIA_ALLOW_DOWNLOAD") == "1" else "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "WANDB_MODE": "disabled",
            "IRODORI_HOST": self.cfg.host,
            "IRODORI_PORT": str(self.cfg.port),
            "IRODORI_HF_CHECKPOINT": self.cfg.checkpoint,
            "IRODORI_MODEL_DEVICE": self.cfg.device,
            "IRODORI_CODEC_DEVICE": self.cfg.device,
            "IRODORI_PRELOAD": "true",
            "IRODORI_VOICES_DIR": str(self.voices_dir),
            "IRODORI_MODEL_LOAD_TIMEOUT": str(self.cfg.load_timeout_sec),
            "PYTORCH_ENABLE_MPS_FALLBACK": "1",
        })
        # Never inherit a virtualenv from the harness process.
        env.pop("VIRTUAL_ENV", None)
        return env

    def _spawn(self) -> None:
        server_dir = self.cfg.server_dir
        if server_dir is None:
            raise TTSError("tts.server_dir is not configured "
                           "(config.toml [tts] server_dir or ADRIA_TTS_SERVER_DIR)")
        if not (server_dir / "pyproject.toml").exists():
            raise TTSError(f"Irodori-TTS-Server not found at {server_dir}")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        logf = (self.log_dir / "tts-server.log").open("ab")
        cmd = ["uv", "run", "--no-sync", "python", "-m", "irodori_openai_tts",
               "--host", self.cfg.host, "--port", str(self.cfg.port)]
        log.info("starting TTS server: %s", " ".join(cmd))
        self._spawn_t0 = time.monotonic()
        self._proc = subprocess.Popen(
            cmd, cwd=server_dir, env=self._server_env(), stdout=logf, stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    def _wait_ready(self) -> None:
        deadline = time.monotonic() + self.cfg.load_timeout_sec
        while time.monotonic() < deadline:
            if self.is_ready():
                if self._proc is not None and getattr(self, "_spawn_t0", None):
                    self.last_start_sec = time.monotonic() - self._spawn_t0
                    self._spawn_t0 = None
                    log.info("TTS server ready in %.1fs", self.last_start_sec)
                return
            if self._proc is not None and self._proc.poll() is not None:
                raise TTSError(f"TTS server exited with code {self._proc.returncode}; "
                               f"see {self.log_dir / 'tts-server.log'}")
            time.sleep(0.5)
        raise TTSError("TTS server did not become ready in time")

    def stop(self) -> None:
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                log.info("stopping TTS server")
                os.killpg(self._proc.pid, signal.SIGTERM)
                try:
                    self._proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(self._proc.pid, signal.SIGKILL)
            self._proc = None

    def shutdown(self) -> None:
        self._stop_evt.set()
        self.stop()

    def _idle_watch(self) -> None:
        while not self._stop_evt.wait(30):
            with self._lock:
                idle = time.monotonic() - self._last_used
                if self._proc is not None and idle >= self.cfg.idle_stop_sec:
                    log.info("TTS idle for %.0fs; stopping server", idle)
                    self.stop()

    # ---------- synthesis ----------

    def synthesize(self, text: str) -> bytes:
        """Synthesize ``text`` to WAV bytes. ``text`` must already have x_ keys removed."""
        self.ensure_running()
        self._last_used = time.monotonic()
        data = self._request(text)
        self._last_used = time.monotonic()
        return data

    def _request(self, text: str) -> bytes:
        body: dict = {
            "model": "irodori-tts",
            "input": text,
            "voice": self.cfg.voice,
            "response_format": "wav",
            "speed": self.cfg.speed,
        }
        irodori: dict = {"chunking_enabled": False}
        if self.cfg.caption:
            irodori["caption"] = self.cfg.caption
        if self.cfg.num_steps:
            irodori["num_steps"] = self.cfg.num_steps
        if self.cfg.seed is not None:
            irodori["seed"] = self.cfg.seed
        body["irodori"] = irodori
        req = urllib.request.Request(
            self.cfg.base_url + "/v1/audio/speech",
            data=json.dumps(body, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = r.read()
        except urllib.error.HTTPError as e:
            raise TTSError(f"TTS HTTP {e.code}: {e.read()[:300]!r}") from e
        return data
