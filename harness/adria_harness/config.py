"""Configuration loading.

All personal content (persona text, voices, local paths) lives in the private
"home" directory, which is passed in via the ADRIA_HOME environment variable.
This module only knows the *shape* of the configuration, never its contents.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(RuntimeError):
    pass


@dataclass
class LLMConfig:
    url: str = "http://127.0.0.1:11434"
    model: str = "qwen3:30b-a3b-instruct-2507-q4_K_M"
    # Ollama unloads the model after this idle period (frees memory).
    keep_alive: str = "10m"
    # Number of past exchanges kept in memory (never written to disk).
    history_turns: int = 8
    options: dict = field(default_factory=lambda: {"temperature": 0.7, "num_ctx": 4096})


@dataclass
class TTSConfig:
    # Checkout of Irodori-TTS-Server. No default: set tts.server_dir in the
    # private config or the ADRIA_TTS_SERVER_DIR environment variable.
    server_dir: Path | None = None
    host: str = "127.0.0.1"
    port: int = 8088
    checkpoint: str = "Aratako/Irodori-TTS-v4-Small"
    device: str = "mps"
    voice: str = "none"
    caption: str = ""
    num_steps: int | None = None
    seed: int | None = None
    speed: float = 1.0
    # Stop the on-demand TTS server after this many idle seconds.
    idle_stop_sec: int = 1800
    load_timeout_sec: int = 600

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class STTConfig:
    model: str = "mlx-community/whisper-large-v3-turbo"
    language: str = "ja"
    vad_threshold: float = 0.5
    # Silence length that ends an utterance. Children pause a lot; keep it generous.
    min_silence_ms: int = 700
    speech_pad_ms: int = 200
    min_utterance_sec: float = 0.35
    max_utterance_sec: float = 15.0
    # Ignore the mic for this long after playback ends (avoid hearing our own tail).
    post_playback_mute_sec: float = 0.4


@dataclass
class Config:
    home: Path
    runtime_dir: Path
    persona_path: Path
    fillers: list[str]
    llm: LLMConfig
    tts: TTSConfig
    stt: STTConfig

    @property
    def voices_dir(self) -> Path:
        return self.home / "voices"


def _merge(dc, values: dict):
    for key, value in values.items():
        if not hasattr(dc, key):
            raise ConfigError(f"unknown config key: {type(dc).__name__}.{key}")
        if key.endswith("_dir") and value is not None:
            value = Path(str(value)).expanduser()
        setattr(dc, key, value)
    return dc


def load_config(home: str | os.PathLike | None = None) -> Config:
    home_str = home or os.environ.get("ADRIA_HOME")
    if not home_str:
        raise ConfigError("ADRIA_HOME is not set (path to the private adria-home directory)")
    home_path = Path(home_str).expanduser().resolve()
    cfg_file = home_path / "config.toml"
    data: dict = {}
    if cfg_file.exists():
        with cfg_file.open("rb") as f:
            data = tomllib.load(f)

    general = data.get("general", {})

    def resolve(p: str | None, default: Path) -> Path:
        if not p:
            return default
        path = Path(p).expanduser()
        return path if path.is_absolute() else home_path / path

    cfg = Config(
        home=home_path,
        runtime_dir=resolve(general.get("runtime_dir"), home_path / "runtime"),
        persona_path=resolve(general.get("persona"), home_path / "personas" / "child.md"),
        fillers=list(general.get("fillers", ["うーんとね。", "えっとね。"])),
        llm=_merge(LLMConfig(), data.get("llm", {})),
        tts=_merge(TTSConfig(), data.get("tts", {})),
        stt=_merge(STTConfig(), data.get("stt", {})),
    )
    env_server_dir = os.environ.get("ADRIA_TTS_SERVER_DIR")
    if env_server_dir:
        cfg.tts.server_dir = Path(env_server_dir).expanduser()
    if cfg.tts.server_dir is not None and not cfg.tts.server_dir.is_absolute():
        cfg.tts.server_dir = home_path / cfg.tts.server_dir
    if cfg.tts.host not in ("127.0.0.1", "localhost", "::1"):
        # Everything must stay on this Mac.
        raise ConfigError("tts.host must be a loopback address")
    cfg.runtime_dir.mkdir(parents=True, exist_ok=True)
    return cfg
