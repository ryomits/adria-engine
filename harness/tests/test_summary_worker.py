import threading
import time

from adria_harness.sessions import Session
from adria_harness.summary_worker import SummaryWorker


class FakeSummarizer:
    def __init__(self):
        self.done: list[str] = []  # first user line of each summarized session
        self.event = threading.Event()

    def summarize(self, session, day):
        self.done.append(session.turns[0][0])
        self.event.set()


def ended(user="u"):
    return Session([(user, "a")])


def test_submitted_session_is_summarized():
    s = FakeSummarizer()
    worker = SummaryWorker(s, may_run=lambda: True, poll_sec=0.01)
    worker.start()
    worker.submit(ended())
    assert s.event.wait(1.0)
    worker.drain(timeout=1.0)


def test_summary_waits_while_a_conversation_is_in_progress():
    s = FakeSummarizer()
    worker = SummaryWorker(s, may_run=lambda: False, poll_sec=0.01)
    worker.start()
    worker.submit(ended())
    time.sleep(0.1)
    assert s.done == []
    worker.drain(timeout=1.0)


def test_drain_finishes_pending_summaries():
    s = FakeSummarizer()
    worker = SummaryWorker(s, may_run=lambda: False, poll_sec=0.01)
    worker.start()
    worker.submit(ended("first"))
    worker.submit(ended("second"))
    worker.drain(timeout=1.0)
    assert s.done == ["first", "second"]


class FailingSummarizer(FakeSummarizer):
    def summarize(self, session, day):
        if session.turns[0][0] == "bad":
            raise RuntimeError("llm down")
        super().summarize(session, day)


def test_a_failed_summary_does_not_stop_the_worker():
    s = FailingSummarizer()
    worker = SummaryWorker(s, may_run=lambda: True, poll_sec=0.01)
    worker.start()
    worker.submit(ended("bad"))
    worker.submit(ended("good"))
    worker.drain(timeout=1.0)
    assert s.done == ["good"]
