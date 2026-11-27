from adria_harness.switch import ConversationSwitch


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def switch(timeout=300):
    clock = Clock()
    return ConversationSwitch(timeout, clock=clock), clock


def test_starts_in_standby():
    s, _ = switch()
    assert not s.active


def test_toggle_starts_a_conversation():
    s, _ = switch()
    s.toggle()
    assert s.active


def test_second_toggle_goes_back_to_standby():
    s, _ = switch()
    s.toggle()
    s.toggle()
    assert not s.active


def test_silence_for_the_timeout_goes_back_to_standby():
    s, clock = switch(timeout=300)
    s.toggle()
    clock.now = 300
    s.expire()
    assert not s.active


def test_expire_reports_the_change():
    s, clock = switch(timeout=300)
    s.toggle()
    clock.now = 300
    assert s.expire()


def test_conversation_stays_on_before_the_timeout():
    s, clock = switch(timeout=300)
    s.toggle()
    clock.now = 299
    s.expire()
    assert s.active


def test_speech_restarts_the_timeout():
    s, clock = switch(timeout=300)
    s.toggle()
    clock.now = 200
    s.touch()
    clock.now = 400
    s.expire()
    assert s.active


def test_standby_does_not_expire_again():
    s, clock = switch(timeout=300)
    clock.now = 1000
    assert not s.expire()


def test_wait_returns_true_once_started():
    s, _ = switch()
    s.toggle()
    assert s.wait_active(timeout=0)


def test_wait_times_out_in_standby():
    s, _ = switch()
    assert not s.wait_active(timeout=0.01)


def test_stop_signal_is_set_in_standby():
    s, _ = switch()
    assert s.standby_signal().is_set()


def test_stop_signal_is_clear_while_active():
    s, _ = switch()
    signal = s.standby_signal()
    s.toggle()
    assert not signal.is_set()
