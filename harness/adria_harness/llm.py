"""Minimal Ollama client (local only, standard library HTTP)."""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Iterator

from .config import LLMConfig


class OllamaClient:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg

    def _post(self, path: str, body: dict, timeout: float = 600):
        req = urllib.request.Request(
            self.cfg.url + path,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        return urllib.request.urlopen(req, timeout=timeout)

    def is_loaded(self) -> bool:
        """True if the model is resident in memory (no reload wait expected)."""
        try:
            with urllib.request.urlopen(self.cfg.url + "/api/ps", timeout=3) as r:
                models = json.load(r).get("models", [])
        except OSError:
            return False
        return any(m.get("name") == self.cfg.model or m.get("model") == self.cfg.model
                   for m in models)

    def chat_stream(self, messages: list[dict]) -> Iterator[str]:
        body = {
            "model": self.cfg.model,
            "messages": messages,
            "stream": True,
            # Conversation needs low latency; reasoning traces must never be spoken.
            "think": False,
            "keep_alive": self.cfg.keep_alive,
            "options": self.cfg.options,
        }
        with self._post("/api/chat", body) as r:
            for line in r:
                if not line.strip():
                    continue
                d = json.loads(line)
                if "error" in d:
                    raise RuntimeError(f"ollama error: {d['error']}")
                chunk = d.get("message", {}).get("content", "")
                if chunk:
                    yield chunk
                if d.get("done"):
                    return

    def chat(self, messages: list[dict], temperature: float | None = None,
             json_output: bool = False) -> str:
        """One non-streamed reply (used for session summaries)."""
        options = dict(self.cfg.options)
        if temperature is not None:
            options["temperature"] = temperature
        body = {
            "model": self.cfg.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "keep_alive": self.cfg.keep_alive,
            "options": options,
        }
        if json_output:
            body["format"] = "json"
        with self._post("/api/chat", body) as r:
            d = json.load(r)
        if "error" in d:
            raise RuntimeError(f"ollama error: {d['error']}")
        return d.get("message", {}).get("content", "")
