"""Commands from the display app: ``runtime/control.jsonl``.

The app appends one JSON line per command, ``{"seq": n, "command": "toggle"}``:

- ``toggle``: start a conversation, or end the running one (a click)
- ``quit``: the app was quit; end the session and exit

Only the app writes the file. Commands written before the harness started are
ignored, so a click while the harness was down does nothing later.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

COMMANDS = ("toggle", "quit")


class ControlInbox:
    def __init__(self, path: Path):
        self.path = path
        self._offset = self._size()

    def _size(self) -> int:
        try:
            return self.path.stat().st_size
        except FileNotFoundError:
            return 0

    def poll(self) -> list[str]:
        """Commands appended since the last call, in order."""
        size = self._size()
        if size < self._offset:  # the file was replaced or truncated
            self._offset = 0
        if size == self._offset:
            return []
        with self.path.open("rb") as f:
            f.seek(self._offset)
            data = f.read(size - self._offset)
        complete = data.rfind(b"\n") + 1  # a line still being written waits for its end
        self._offset += complete
        commands = []
        for line in data[:complete].splitlines():
            try:
                command = json.loads(line).get("command")
            except (ValueError, AttributeError):
                log.warning("ignored a malformed control line")
                continue
            if command in COMMANDS:
                commands.append(command)
            else:
                log.warning("ignored unknown control command %r", command)
        return commands
