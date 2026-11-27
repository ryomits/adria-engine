"""Applies display commands and timeouts to the conversation.

Called every ``tick`` (a fraction of a second) by the harness:

- ``toggle`` from the display starts or ends the conversation
- ``quit`` from the display asks the harness to exit
- silence for the timeout puts the conversation in standby
- a session with no turn for the timeout is ended and handed on for its summary

Ending a conversation by click keeps the session: a new click within the
timeout continues it with the same short-term history.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from .control import ControlInbox
from .sessions import Session, SessionBook
from .switch import ConversationSwitch

log = logging.getLogger(__name__)


class Controller:
    def __init__(self, inbox: ControlInbox, switch: ConversationSwitch, sessions: SessionBook,
                 on_session_end: Callable[[Session], None], on_quit: Callable[[], None]):
        self.inbox = inbox
        self.switch = switch
        self.sessions = sessions
        self.on_session_end = on_session_end
        self.on_quit = on_quit

    def tick(self) -> None:
        for command in self.inbox.poll():
            if command == "toggle":
                active = self.switch.toggle()
                log.info("conversation %s by click", "started" if active else "ended")
            elif command == "quit":
                log.info("the display app was quit")
                self.on_quit()
        if self.switch.expire():
            log.info("no speech for %.0f s; back to standby", self.switch.timeout_sec)
        ended = self.sessions.end_if_idle()
        if ended is not None:
            self.on_session_end(ended)
