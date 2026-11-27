"""Only one voice loop at a time.

Both the display app and ``start.command`` can start the harness; a second one
would fight over the microphone and the signal files, so it refuses to start.
"""

from __future__ import annotations

import fcntl
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class AlreadyRunning(RuntimeError):
    pass


@contextmanager
def single_instance(runtime_dir: Path) -> Iterator[Path]:
    """Hold ``runtime/harness.lock`` while the block runs.

    The OS releases the lock if the process dies, so a crash leaves nothing stale.
    """
    path = runtime_dir / "harness.lock"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise AlreadyRunning("another ADRIA voice loop is already running") from None
        try:
            yield path
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
