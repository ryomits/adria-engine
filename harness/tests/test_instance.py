import pytest

from adria_harness.instance import AlreadyRunning, single_instance


def test_first_instance_gets_the_lock(tmp_path):
    with single_instance(tmp_path) as lock:
        assert lock is not None


def test_second_instance_is_refused(tmp_path):
    with single_instance(tmp_path), pytest.raises(AlreadyRunning):
        with single_instance(tmp_path):
            pass


def test_lock_is_released_on_exit(tmp_path):
    with single_instance(tmp_path):
        pass
    with single_instance(tmp_path) as lock:
        assert lock is not None
