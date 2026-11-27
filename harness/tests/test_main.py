import logging

from adria_harness.main import log_level


def test_info_by_default():
    assert log_level(verbose=False, quiet=False) == logging.INFO


def test_quiet_keeps_only_warnings():
    assert log_level(verbose=False, quiet=True) == logging.WARNING


def test_verbose_shows_debug():
    assert log_level(verbose=True, quiet=False) == logging.DEBUG
