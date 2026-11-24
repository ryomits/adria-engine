"""ADRIA harness command line.

    adria voice            microphone conversation loop (speaker -> persona)
    adria chat             text conversation loop (replies are spoken)
    adria enroll NAME      register a speaker's voiceprint (microphone or --wav)
    adria speakers         list enrolled speakers and their personas
    adria forget NAME      delete a speaker's voiceprint
    adria identify WAV...  show which enrolled speaker each file sounds like
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
import signal
import sys
import threading
import time
import uuid
from pathlib import Path

import numpy as np

# Runtime is offline-only: models must already be cached by the setup script.
if os.environ.get("ADRIA_ALLOW_DOWNLOAD") != "1":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

from .config import Config, load_config  # noqa: E402
from .conversation import Conversation  # noqa: E402
from .llm import OllamaClient  # noqa: E402
from .memory import MemoryStore, Summarizer  # noqa: E402
from .persona import load_persona  # noqa: E402
from .player import Player  # noqa: E402
from .playqueue import PlayQueue  # noqa: E402
from .sessions import SessionBook  # noqa: E402
from .speaker import (  # noqa: E402
    EcapaEmbedder,
    SpeakerIdentifier,
    SpeakerMatch,
    VoiceprintStore,
    persona_for,
)
from .status import Metrics, Status  # noqa: E402
from .summary_worker import SummaryWorker  # noqa: E402
from .transcript import TranscriptLog  # noqa: E402
from .tts import IrodoriTTS  # noqa: E402

log = logging.getLogger("adria")

MAKE_VOICE_TEXT = "こんにちは。きょうは、なにしてあそぶ？いっしょに、おはなししようね。"
SUMMARY_TEMPERATURE = 0.2
EXIT_SUMMARY_TIMEOUT_SEC = 120
HOUSEKEEPING_SEC = 5


def speaker_identifier(cfg: Config) -> SpeakerIdentifier:
    sp = cfg.speakers
    return SpeakerIdentifier(EcapaEmbedder(sp.model_dir), VoiceprintStore(sp.voiceprint_dir),
                             sp.threshold, sp.margin, sp.min_audio_sec)


class App:
    def __init__(self, cfg: Config, mute: bool = False):
        self.cfg = cfg
        self.queue = PlayQueue(cfg.runtime_dir)
        self.queue.clear()  # never replay leftovers from a previous run
        self.status = Status(cfg.runtime_dir)
        self.metrics = Metrics(cfg.runtime_dir)
        self.tts = IrodoriTTS(cfg.tts, cfg.voices_dir, cfg.runtime_dir / "logs")
        self.llm = OllamaClient(cfg.llm)
        self.player = Player(self.queue, self.tts, self.status, self.metrics, mute=mute)
        self.busy = threading.Event()  # a reply turn is in progress (mic is muted)
        self.sessions = SessionBook(cfg.memory.idle_end_sec)
        self.memory = MemoryStore(cfg.memory_dir)
        self.transcript = TranscriptLog(cfg.transcript_dir, cfg.memory.transcript_retention_days)
        summarizer = Summarizer(
            lambda messages: self.llm.chat(messages, temperature=SUMMARY_TEMPERATURE),
            self.memory, cfg.memory.max_chars,
            personas=lambda name: load_persona(cfg.persona_dir, name))
        self.summaries = SummaryWorker(summarizer, may_run=self._quiet)
        self.conv = Conversation(cfg, self.llm, self.queue, self.status, self.metrics,
                                 sessions=self.sessions, memory=self.memory,
                                 transcript=self.transcript,
                                 on_session_end=self.summaries.submit)
        self._stop = threading.Event()
        self._housekeeper = threading.Thread(target=self._housekeep, daemon=True,
                                             name="housekeeping")

    def __enter__(self):
        self.transcript.purge()
        self.summaries.start()
        self._housekeeper.start()
        self.player.start()
        self.tts.prestart()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        ended = self.sessions.end()
        if ended is not None:
            self.summaries.submit(ended)
            print("saving a summary of this conversation ...")
        self.summaries.drain(EXIT_SUMMARY_TIMEOUT_SEC)
        self.player.stop()
        self.tts.shutdown()
        self.status.update(listening=False, speaking=False)

    def _quiet(self) -> bool:
        """Nobody is talking and nothing is being said: the LLM is free for a summary."""
        return not self.busy.is_set() and self.player.wait_idle(timeout=0)

    def _housekeep(self) -> None:
        last_purge = time.monotonic()
        while not self._stop.wait(HOUSEKEEPING_SEC):
            ended = self.sessions.end_if_idle()
            if ended is not None:
                self.summaries.submit(ended)
            if time.monotonic() - last_purge > 3600:
                self.transcript.purge()
                last_purge = time.monotonic()

    def mic_muted(self) -> bool:
        if self.busy.is_set():
            return True
        tail = time.monotonic() - self.player.last_playback_end
        return tail < self.cfg.stt.post_playback_mute_sec

    def run_turn(self, user_text: str, speech_end: float | None = None,
                 stt_sec: float | None = None, persona: str | None = None,
                 speaker: SpeakerMatch | None = None) -> dict:
        """One full reply turn; blocks until the reply has been spoken."""
        turn_id = uuid.uuid4().hex[:8]
        t0 = speech_end or time.monotonic()
        reply = self.conv.respond(user_text, persona_name=persona, speaker=speaker,
                                  turn_id=turn_id)
        self.player.wait_idle()
        first = self.player.first_play_at.pop(turn_id, None)
        result = {
            "turn_id": turn_id,
            "stt_sec": None if stt_sec is None else round(stt_sec, 3),
            "to_first_audio_sec": None if first is None else round(first - t0, 3),
            "total_sec": round(time.monotonic() - t0, 3),
        }
        self.metrics.record("turn", **result)
        print(f"  ADRIA ({persona or self.cfg.default_persona}): {reply}")
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
            app.run_turn(line, persona=args.persona)


def route(cfg: Config, match: SpeakerMatch | None) -> str:
    return persona_for(match, cfg.speakers.map, cfg.default_persona)


def describe(match: SpeakerMatch | None, persona: str) -> str:
    who = "unknown" if match is None or match.speaker is None else match.speaker
    score = "" if match is None else f" {match.score:.2f}"
    return f"{who}{score} -> {persona}"


def cmd_voice(cfg: Config, args) -> None:
    from concurrent.futures import ThreadPoolExecutor

    from .stt import MicListener, Transcriber

    stt = Transcriber(cfg.stt)
    print("loading speech recognition ...")
    stt.warmup()
    identifier = speaker_identifier(cfg)
    if identifier.store.load_all():
        identifier.embed.load()
    # Speaker identification runs next to speech recognition, not after it.
    side = ThreadPoolExecutor(max_workers=1, thread_name_prefix="speaker")
    stop = threading.Event()
    with App(cfg, mute=args.mute) as app:
        # "listening" covers the child's speech and its transcription; waiting
        # for speech is "idle".
        listener = MicListener(
            cfg.stt, is_muted=app.mic_muted,
            on_speech_start=lambda: app.status.update(listening=True),
            on_speech_discard=lambda: app.status.update(listening=False),
        )
        print("ready — Ctrl-C to quit")
        try:
            for audio, speech_end in listener.utterances(stop):
                app.busy.set()
                try:
                    t = time.monotonic()
                    who = side.submit(identifier.identify, audio)
                    text = stt.transcribe(audio)
                    stt_sec = time.monotonic() - t
                    match = who.result()
                    persona = route(cfg, match)
                    app.metrics.record("stt", audio_sec=round(len(audio) / 16000, 2),
                                       stt_sec=round(stt_sec, 3), empty=not text)
                    app.metrics.record("speaker", speaker=match.speaker,
                                       score=round(match.score, 3), persona=persona,
                                       sec=round(time.monotonic() - t, 3))
                    if not text:
                        continue
                    print(f"  you ({describe(match, persona)}): {text}")
                    app.run_turn(text, speech_end=speech_end, stt_sec=stt_sec,
                                 persona=persona, speaker=match)
                finally:
                    app.busy.clear()
                    app.status.update(listening=False)
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()
            side.shutdown(wait=False)


def read_wav_16k(path) -> np.ndarray:
    import soundfile as sf

    from .stt import SAMPLE_RATE

    audio, sr = sf.read(path, dtype="float32", always_2d=True)
    audio = audio[:, 0]
    if sr != SAMPLE_RATE:
        n = int(len(audio) * SAMPLE_RATE / sr)
        audio = np.interp(np.linspace(0, len(audio), n, endpoint=False),
                          np.arange(len(audio)), audio).astype("float32")
    return audio


def cmd_e2e(cfg: Config, args) -> None:
    """Feed WAV files as if they were spoken (no microphone needed)."""
    from .stt import Transcriber

    stt = Transcriber(cfg.stt)
    stt.warmup()
    identifier = speaker_identifier(cfg)
    results = []
    with App(cfg, mute=args.mute) as app:
        for path in args.wavs:
            audio = read_wav_16k(path)
            speech_end = time.monotonic()
            match = identifier.identify(audio)
            persona = args.persona or route(cfg, match)
            text = stt.transcribe(audio)
            stt_sec = time.monotonic() - speech_end
            print(f"\n[{Path(path).name}] you ({describe(match, persona)}): {text}")
            if text:
                results.append(app.run_turn(text, speech_end=speech_end, stt_sec=stt_sec,
                                            persona=persona, speaker=match))
    vals = [r["to_first_audio_sec"] for r in results if r["to_first_audio_sec"] is not None]
    if vals:
        print(f"\nturns={len(vals)} speech-end -> first audio: "
              f"min={min(vals):.2f}s max={max(vals):.2f}s avg={sum(vals) / len(vals):.2f}s")


def cmd_enroll(cfg: Config, args) -> None:
    """Record 10-30 s of one person's speech and save the voiceprint."""
    from .speaker import EnrollmentError, enroll_voiceprint

    identifier = speaker_identifier(cfg)
    if args.wav:
        segments = [read_wav_16k(p) for p in args.wav]
    else:
        segments = _record_enrollment(cfg, args.seconds)
    try:
        voiceprint = enroll_voiceprint(segments, identifier.embed, cfg.speakers.min_enroll_sec)
    except EnrollmentError as e:
        sys.exit(f"enrollment failed: {e}")
    others = {k: v for k, v in identifier.store.load_all().items() if k != args.name}
    path = identifier.store.save(args.name, voiceprint)
    self_scores = [float(np.dot(voiceprint, identifier.embed(s))) for s in segments
                   if len(s) / 16000 >= cfg.speakers.min_audio_sec]
    print(f"saved {path.name} from {sum(len(s) for s in segments) / 16000:.1f}s of speech")
    if self_scores:
        print(f"  consistency: min {min(self_scores):.2f}, mean {np.mean(self_scores):.2f} "
              f"(threshold {cfg.speakers.threshold:.2f})")
    for other, vp in others.items():
        sim = float(np.dot(voiceprint, vp))
        note = "  <- close; this pair may be confused" if sim > cfg.speakers.threshold else ""
        print(f"  similarity to {other}: {sim:.2f}{note}")
    persona = cfg.speakers.map.get(args.name)
    print(f"  persona: {persona or cfg.default_persona + ' (not mapped in [speakers.map])'}")


def _record_enrollment(cfg: Config, seconds: float) -> list:
    from .stt import SAMPLE_RATE, MicListener

    stop = threading.Event()
    listener = MicListener(cfg.stt, is_muted=lambda: False)
    print(f"speak naturally for about {seconds:.0f} seconds (several sentences; "
          "pauses are fine). Ctrl-C to stop early.")
    segments, total = [], 0.0
    try:
        for audio, _ in listener.utterances(stop):
            segments.append(audio)
            total += len(audio) / SAMPLE_RATE
            print(f"  {total:4.1f}s / {seconds:.0f}s")
            if total >= seconds:
                break
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
    return segments


def cmd_speakers(cfg: Config, args) -> None:
    store = VoiceprintStore(cfg.speakers.voiceprint_dir)
    names = sorted(store.load_all())
    if not names:
        print("no speakers enrolled; everyone gets the default persona "
              f"({cfg.default_persona})")
    for name in names:
        print(f"{name} -> {cfg.speakers.map.get(name, cfg.default_persona)}")
    for name in sorted(set(cfg.speakers.map) - set(names)):
        print(f"{name} -> {cfg.speakers.map[name]} (not enrolled)")


def cmd_forget(cfg: Config, args) -> None:
    VoiceprintStore(cfg.speakers.voiceprint_dir).remove(args.name)
    print(f"deleted the voiceprint of {args.name}")


def cmd_identify(cfg: Config, args) -> None:
    identifier = speaker_identifier(cfg)
    for path in args.wavs:
        match = identifier.identify(read_wav_16k(path))
        print(f"{Path(path).name}: {describe(match, route(cfg, match))}")


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


def _exit_on_signal(signum, frame):
    raise SystemExit(128 + signum)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="adria")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    def with_mute(sp):
        sp.add_argument("--mute", action="store_true",
                        help="do not output sound (playback is only timed)")
        return sp

    with_mute(sub.add_parser("voice")).set_defaults(func=cmd_voice)
    sp = with_mute(sub.add_parser("chat"))
    sp.add_argument("--persona", help="persona to talk to (default: [personas] default)")
    sp.set_defaults(func=cmd_chat)
    sp = sub.add_parser("enroll")
    sp.add_argument("name", help="speaker id (lowercase), mapped in [speakers.map]")
    sp.add_argument("--seconds", type=float, default=None,
                    help="speech to record (default: speakers.enroll_sec)")
    sp.add_argument("--wav", nargs="+", help="enroll from files instead of the microphone")
    sp.set_defaults(func=cmd_enroll)
    sub.add_parser("speakers").set_defaults(func=cmd_speakers)
    sp = sub.add_parser("forget")
    sp.add_argument("name")
    sp.set_defaults(func=cmd_forget)
    sp = sub.add_parser("identify")
    sp.add_argument("wavs", nargs="+")
    sp.set_defaults(func=cmd_identify)
    sp = with_mute(sub.add_parser("say"))
    sp.add_argument("text")
    sp.set_defaults(func=cmd_say)
    sp = with_mute(sub.add_parser("e2e"))
    sp.add_argument("wavs", nargs="+")
    sp.add_argument("--persona", help="skip speaker identification and use this persona")
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
    # Closing the Terminal window (SIGHUP) or stop.sh (SIGTERM) must still run
    # the cleanup that stops the TTS server; it runs in its own session and
    # would otherwise be left behind holding several GB of memory.
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, _exit_on_signal)
    cfg = load_config()
    if getattr(args, "seconds", "unset") is None:
        args.seconds = cfg.speakers.enroll_sec
    args.func(cfg, args)


if __name__ == "__main__":
    main()
