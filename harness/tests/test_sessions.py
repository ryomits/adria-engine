from adria_harness.sessions import SessionBook


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def book(idle_sec=300):
    clock = Clock()
    return SessionBook(idle_sec, clock=clock), clock


def test_history_is_empty_for_a_new_session():
    b, _ = book()
    assert b.history() == []


def test_recorded_turns_become_chat_history():
    b, _ = book()
    b.record("いちごすき", "おいしいよね。")
    assert b.history() == [{"role": "user", "content": "いちごすき"},
                           {"role": "assistant", "content": "おいしいよね。"}]


def test_history_is_limited_to_the_last_turns():
    b, _ = book()
    for i in range(5):
        b.record(f"u{i}", f"a{i}")
    assert b.history(max_turns=2)[0]["content"] == "u3"


def test_idle_session_ends_after_the_timeout():
    b, clock = book(idle_sec=300)
    b.record("いちごすき", "おいしいよね。")
    clock.now = 300
    assert b.end_if_idle().turns == [("いちごすき", "おいしいよね。")]


def test_active_session_does_not_end_before_the_timeout():
    b, clock = book(idle_sec=300)
    b.record("いちごすき", "おいしいよね。")
    clock.now = 299
    assert b.end_if_idle() is None


def test_after_an_idle_end_history_starts_over():
    b, clock = book(idle_sec=300)
    b.record("いちごすき", "おいしいよね。")
    clock.now = 300
    b.end_if_idle()
    assert b.history() == []


def test_an_empty_session_is_not_reported_as_ended():
    b, _ = book()
    assert b.end() is None


def test_end_returns_the_open_session():
    b, _ = book()
    b.record("いちごすき", "おいしいよね。")
    assert b.end().turns == [("いちごすき", "おいしいよね。")]
