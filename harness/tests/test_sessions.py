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
    b.begin("child")
    assert b.history("child") == []


def test_recorded_turns_become_chat_history():
    b, _ = book()
    b.begin("child")
    b.record("child", "いちごすき", "おいしいよね。")
    assert b.history("child") == [{"role": "user", "content": "いちごすき"},
                                  {"role": "assistant", "content": "おいしいよね。"}]


def test_history_is_limited_to_the_last_turns():
    b, _ = book()
    b.begin("child")
    for i in range(5):
        b.record("child", f"u{i}", f"a{i}")
    assert b.history("child", max_turns=2)[0]["content"] == "u3"


def test_switching_persona_ends_the_previous_session():
    b, _ = book()
    b.begin("child")
    b.record("child", "いちごすき", "おいしいよね。")
    assert b.begin("parent").persona == "child"


def test_switching_persona_starts_with_empty_history():
    b, _ = book()
    b.begin("child")
    b.record("child", "いちごすき", "おいしいよね。")
    b.begin("parent")
    assert b.history("parent") == []


def test_history_of_another_persona_is_never_returned():
    b, _ = book()
    b.begin("child")
    b.record("child", "いちごすき", "おいしいよね。")
    b.begin("parent")
    assert b.history("child") == []


def test_continuing_with_the_same_persona_ends_nothing():
    b, _ = book()
    b.begin("child")
    b.record("child", "いちごすき", "おいしいよね。")
    assert b.begin("child") is None


def test_a_session_without_turns_is_not_reported_as_ended():
    b, _ = book()
    b.begin("child")
    assert b.begin("parent") is None


def test_idle_session_ends_after_the_timeout():
    b, clock = book(idle_sec=300)
    b.begin("child")
    b.record("child", "いちごすき", "おいしいよね。")
    clock.now = 301
    assert b.end_if_idle().persona == "child"


def test_active_session_does_not_end_before_the_timeout():
    b, clock = book(idle_sec=300)
    b.begin("child")
    b.record("child", "いちごすき", "おいしいよね。")
    clock.now = 299
    assert b.end_if_idle() is None


def test_after_an_idle_end_history_starts_over():
    b, clock = book(idle_sec=300)
    b.begin("child")
    b.record("child", "いちごすき", "おいしいよね。")
    clock.now = 301
    b.end_if_idle()
    b.begin("child")
    assert b.history("child") == []


def test_end_returns_the_open_session():
    b, _ = book()
    b.begin("child")
    b.record("child", "いちごすき", "おいしいよね。")
    assert b.end().turns == [("いちごすき", "おいしいよね。")]
