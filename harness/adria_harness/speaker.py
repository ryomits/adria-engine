"""Speaker identification by voiceprint (ECAPA-TDNN embeddings, local only).

Used only to choose a persona, never for authentication. Anything uncertain
(unknown voice, too short, two enrolled voices too close to call) is reported
as unknown, and unknown speakers get the default (child) persona.

Voiceprints are unit vectors saved as ``<dir>/<speaker>.npy``. The directory is
outside version control (ignored in both repositories); no audio is stored.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .persona import check_name

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000
ECAPA_SOURCE = "speechbrain/spkrec-ecapa-voxceleb"

Embedder = Callable[[np.ndarray], np.ndarray]


class EnrollmentError(RuntimeError):
    pass


@dataclass(frozen=True)
class SpeakerMatch:
    speaker: str | None  # None: unknown
    score: float  # cosine similarity to the best enrolled voice (0 if none)


def _unit(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32).reshape(-1)
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def match_voiceprint(embedding: np.ndarray, prints: Mapping[str, np.ndarray],
                     threshold: float, margin: float) -> SpeakerMatch:
    """Best enrolled speaker, if it is both close enough and clearly ahead of the rest."""
    if not prints:
        return SpeakerMatch(None, 0.0)
    e = _unit(embedding)
    scores = sorted(((float(np.dot(e, _unit(p))), name) for name, p in prints.items()),
                    reverse=True)
    best, name = scores[0]
    runner_up = scores[1][0] if len(scores) > 1 else -1.0
    if best < threshold or best - runner_up < margin:
        return SpeakerMatch(None, best)
    return SpeakerMatch(name, best)


def persona_for(match: SpeakerMatch | None, mapping: Mapping[str, str], default: str) -> str:
    if match is None or match.speaker is None:
        return default
    return mapping.get(match.speaker, default)


class VoiceprintStore:
    def __init__(self, directory: Path):
        self.dir = directory

    def _path(self, speaker: str) -> Path:
        return self.dir / f"{check_name(speaker)}.npy"

    def save(self, speaker: str, voiceprint: np.ndarray) -> Path:
        path = self._path(speaker)
        self.dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        part = path.with_name(path.name + ".part")
        fd = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            np.save(f, _unit(voiceprint))
        os.replace(part, path)
        return path

    def remove(self, speaker: str) -> None:
        self._path(speaker).unlink(missing_ok=True)

    def load_all(self) -> dict[str, np.ndarray]:
        if not self.dir.is_dir():
            return {}
        return {p.stem: np.load(p) for p in sorted(self.dir.glob("*.npy"))}


def enroll_voiceprint(segments: Iterable[np.ndarray], embed: Embedder,
                      min_total_sec: float) -> np.ndarray:
    """Average the embeddings of several utterances into one voiceprint."""
    segments = [s for s in segments if len(s)]
    total = sum(len(s) for s in segments) / SAMPLE_RATE
    if total < min_total_sec:
        raise EnrollmentError(f"only {total:.1f}s of speech; need at least {min_total_sec:.0f}s")
    embeddings = [_unit(embed(s)) for s in segments]
    return _unit(np.mean(embeddings, axis=0))


class SpeakerIdentifier:
    def __init__(self, embed: Embedder, store: VoiceprintStore, threshold: float,
                 margin: float, min_audio_sec: float):
        self.embed = embed
        self.store = store
        self.threshold = threshold
        self.margin = margin
        self.min_audio_sec = min_audio_sec

    def identify(self, audio: np.ndarray) -> SpeakerMatch:
        if len(audio) / SAMPLE_RATE < self.min_audio_sec:
            return SpeakerMatch(None, 0.0)
        # Voiceprints are re-read each time so a new enrollment applies at once.
        prints = self.store.load_all()
        if not prints:
            return SpeakerMatch(None, 0.0)
        return match_voiceprint(self.embed(audio), prints, self.threshold, self.margin)


class EcapaEmbedder:
    """SpeechBrain ECAPA-TDNN speaker embedding on the CPU (~30 ms per utterance)."""

    def __init__(self, model_dir: Path):
        self.model_dir = model_dir
        self._model = None
        self._lock = threading.Lock()

    def load(self) -> None:
        with self._lock:
            if self._model is not None:
                return
            import warnings

            from speechbrain.inference.speaker import EncoderClassifier

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._model = EncoderClassifier.from_hparams(
                    source=ECAPA_SOURCE, savedir=str(self.model_dir),
                    run_opts={"device": "cpu"})

    def __call__(self, audio: np.ndarray) -> np.ndarray:
        import torch

        self.load()
        with self._lock, torch.no_grad():
            x = torch.from_numpy(np.asarray(audio, dtype=np.float32)).unsqueeze(0)
            emb = self._model.encode_batch(x)
        return _unit(emb.squeeze().cpu().numpy())
