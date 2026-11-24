"""ADRIA harness command line.

    adria voice            microphone conversation loop
    adria chat             text conversation loop (replies are spoken)
    adria say TEXT         speak one line through the queue
    adria e2e WAV...       loopback test: WAV -> STT -> LLM -> TTS, with latency report
    adria stt-file WAV     transcribe a file
    adria make-voice NAME  create a reference voice from the configured caption
    adria tts-server start|stop|status
    adria fetch-models     download all model weights (setup only; needs ADRIA_ALLOW_DOWNLOAD=1)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import time
import uuid
from pathlib import Path

# Runtime is offline-only: models must already be cached by the setup script.
if os.environ.get("ADRIA_ALLOW_DOWNLOAD") != "1":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

from .config import Config, load_config  # noqa: E402
from .conversation import Conversation  # noqa: E402
from .llm import OllamaClient  # noqa: E402
from .player import Player  # noqa: E402
from .playqueue import PlayQueue  # noqa: E402
from .status import Metrics, Status  # noqa: E402
from .tts import IrodoriTTS  # noqa: E402

log = logging.getLogger("adria")

MAKE_VOICE_TEXT = "こんにちは。きょうは、なにしてあそぶ？いっしょに、おはなししようね。"


class App:
    def __init__(self, cfg: Config, mute: bool = False):
        self.cfg = cfg
        self.queue = PlayQueue(cfg.runtime_dir)
        self.queue.clear()  # never replay leftovers from a previous run
        self.status = Status(cfg.runtime_dir)
        self.metrics = Metrics(cfg.runtime_dir)
        self.tts = IrodoriTTS(cfg.tts, cfg.voices_dir, cfg.runtime_dir / "logs")
        self.llm = OllamaClient(cfg.llm)
        self.player = Player(self.queue, self.tts, self.status, self.metrics, cfg.runtime_dir,
                             mute=mute)
        self.conv = Conversation(cfg, self.llm, self.queue, self.status, self.metrics)
        self.busy = threading.Event()  # a reply turn is in progress (mic is muted)

    def __enter__(self):
        self.player.start()
        self.tts.prestart()
        return self

    def __exit__(self, *exc):
        self.player.stop()
        self.tts.shutdown()
        self.status.update(listening=False, speaking=False)

    def mic_muted(self) -> bool:
        if self.busy.is_set():
            return True
        tail = time.monotonic() - self.player.last_playback_end
        return tail < self.cfg.stt.post_playback_mute_sec

    def run_turn(self, user_text: str, speech_end: float | None = None,
                 stt_sec: float | None = None) -> dict:
        """One full reply turn; blocks until the reply has been spoken."""
        turn_id = uuid.uuid4().hex[:8]
        t0 = speech_end or time.monotonic()
        reply = self.conv.respond(user_text, turn_id=turn_id)
        self.player.wait_idle()
        first = self.player.first_play_at.pop(turn_id, None)
        result = {
            "turn_id": turn_id,
            "stt_sec": None if stt_sec is None else round(stt_sec, 3),
            "to_first_audio_sec": None if first is None else round(first - t0, 3),
            "total_sec": round(time.monotonic() - t0, 3),
        }
        self.metrics.record("turn", **result)
        print(f"  ADRIA: {reply}")
        print(f"  [latency] {result}")
        return result


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    for noisy in ("urllib3", "httpx", "numba", "matplotlib"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def cmd_chat(cfg: Config, args) -> None:
    with App(cfg, mute=args.mute) as app:
        print("text chat — empty line or Ctrl-D to quit")
        while True:
            try:
                line = input("you> ").strip()
            except EOFError:
                break
            if not line:
                break
            app.run_turn(line)


def cmd_voice(cfg: Config, args) -> None:
    from .stt import MicListener, Transcriber

    stt = Transcriber(cfg.stt)
    print("loading speech recognition ...")
    stt.warmup()
    stop = threading.Event()
    with App(cfg, mute=args.mute) as app:
        listener = MicListener(cfg.stt, is_muted=app.mic_muted)
        app.status.update(listening=True)
        print("listening — Ctrl-C to quit")
        try:
            for audio, speech_end in listener.utterances(stop):
                app.busy.set()
                app.status.update(listening=False)
                try:
                    t = time.monotonic()
                    text = stt.transcribe(audio)
                    stt_sec = time.monotonic() - t
                    if not text:
                        continue
                    print(f"  you: {text}")
                    app.run_turn(text, speech_end=speech_end, stt_sec=stt_sec)
                finally:
                    app.busy.clear()
                    app.status.update(listening=True)
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()


def cmd_e2e(cfg: Config, args) -> None:
    """Feed WAV files as if they were spoken (no microphone needed)."""
    import soundfile as sf

    from .stt import SAMPLE_RATE, Transcriber

    stt = Transcriber(cfg.stt)
    stt.warmup()
    results = []
    with App(cfg, mute=args.mute) as app:
        for path in args.wavs:
            audio, sr = sf.read(path, dtype="float32", always_2d=True)
            audio = audio[:, 0]
            if sr != SAMPLE_RATE:
                import numpy as np

                n = int(len(audio) * SAMPLE_RATE / sr)
                audio = np.interp(np.linspace(0, len(audio), n, endpoint=False),
                                  np.arange(len(audio)), audio).astype("float32")
            speech_end = time.monotonic()
            text = stt.transcribe(audio)
            stt_sec = time.monotonic() - speech_end
            print(f"\n[{Path(path).name}] you: {text}")
            if text:
                results.append(app.run_turn(text, speech_end=speech_end, stt_sec=stt_sec))
    vals = [r["to_first_audio_sec"] for r in results if r["to_first_audio_sec"] is not None]
    if vals:
        print(f"\nturns={len(vals)} speech-end -> first audio: "
              f"min={min(vals):.2f}s max={max(vals):.2f}s avg={sum(vals) / len(vals):.2f}s")


def cmd_say(cfg: Config, args) -> None:
    with App(cfg, mute=args.mute) as app:
        app.queue.push({"id": "say-0", "turn_id": "say", "seq": 0, "text": args.text,
                        "x_expression": "neutral"})
        time.sleep(0.2)
        app.player.wait_idle()


def cmd_stt_file(cfg: Config, args) -> None:
    import soundfile as sf

    from .stt import Transcriber

    stt = Transcriber(cfg.stt)
    for path in args.wavs:
        audio, sr = sf.read(path, dtype="float32", always_2d=True)
        if sr != 16000:
            sys.exit(f"{path}: expected 16 kHz audio, got {sr}")
        t = time.monotonic()
        print(f"{path}: {stt.transcribe(audio[:, 0])}  ({time.monotonic() - t:.2f}s)")


def cmd_make_voice(cfg: Config, args) -> None:
    """Create a fixed reference voice so every line uses the same timbre."""
    if not cfg.tts.caption:
        sys.exit("tts.caption is empty in config.toml")
    tts = IrodoriTTS(cfg.tts, cfg.voices_dir, cfg.runtime_dir / "logs")
    saved_voice = cfg.tts.voice
    cfg.tts.voice = "none"
    try:
        wav = tts.synthesize(args.text)
    finally:
        cfg.tts.voice = saved_voice
        tts.shutdown()
    cfg.voices_dir.mkdir(parents=True, exist_ok=True)
    out = cfg.voices_dir / f"{args.name}.wav"
    out.write_bytes(wav)
    print(f"saved {out}. Set tts.voice = \"{args.name}\" in config.toml to use it.")


def cmd_tts_server(cfg: Config, args) -> None:
    tts = IrodoriTTS(cfg.tts, cfg.voices_dir, cfg.runtime_dir / "logs")
    if args.action == "status":
        print(tts.health() or "not running")
    elif args.action == "start":
        t = time.monotonic()
        tts.ensure_running()
        print(f"ready ({time.monotonic() - t:.1f}s). Note: the server stops when this "
              "command exits; the harness manages its own instance.")
        tts.shutdown()
    elif args.action == "stop":
        import subprocess

        subprocess.run(["pkill", "-f", "irodori_openai_tts"], check=False)


def cmd_fetch_models(cfg: Config, args) -> None:
    import subprocess

    if os.environ.get("ADRIA_ALLOW_DOWNLOAD") != "1":
        sys.exit("fetch-models needs ADRIA_ALLOW_DOWNLOAD=1 (runtime is offline-only)")
    print(f"LLM: ollama pull {cfg.llm.model}")
    subprocess.run(["ollama", "pull", cfg.llm.model], check=True)
    from huggingface_hub import snapshot_download

    print(f"STT: {cfg.stt.model}")
    snapshot_download(cfg.stt.model)
    print(f"TTS: {cfg.tts.checkpoint} (+ codec) via first server start")
    tts = IrodoriTTS(cfg.tts, cfg.voices_dir, cfg.runtime_dir / "logs")
    try:
        tts.ensure_running()
    finally:
        tts.shutdown()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="adria")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    def with_mute(sp):
        sp.add_argument("--mute", action="store_true",
                        help="do not output sound (playback is only timed)")
        return sp

    with_mute(sub.add_parser("voice")).set_defaults(func=cmd_voice)
    with_mute(sub.add_parser("chat")).set_defaults(func=cmd_chat)
    sp = with_mute(sub.add_parser("say"))
    sp.add_argument("text")
    sp.set_defaults(func=cmd_say)
    sp = with_mute(sub.add_parser("e2e"))
    sp.add_argument("wavs", nargs="+")
    sp.set_defaults(func=cmd_e2e)
    sp = sub.add_parser("stt-file")
    sp.add_argument("wavs", nargs="+")
    sp.set_defaults(func=cmd_stt_file)
    sp = sub.add_parser("make-voice")
    sp.add_argument("name")
    sp.add_argument("--text", default=MAKE_VOICE_TEXT)
    sp.set_defaults(func=cmd_make_voice)
    sub.add_parser("fetch-models").set_defaults(func=cmd_fetch_models)
    sp = sub.add_parser("tts-server")
    sp.add_argument("action", choices=["start", "stop", "status"])
    sp.set_defaults(func=cmd_tts_server)

    args = p.parse_args(argv)
    _setup_logging(args.verbose)
    args.func(load_config(), args)


if __name__ == "__main__":
    main()
