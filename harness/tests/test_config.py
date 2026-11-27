import pytest

from adria_harness.config import ConfigError, load_config


def home(tmp_path, toml=""):
    (tmp_path / "config.toml").write_text(toml, encoding="utf-8")
    return load_config(tmp_path)


def test_the_persona_lives_in_the_home(tmp_path):
    assert home(tmp_path).persona_path == tmp_path / "persona.md"


def test_memory_lives_in_the_home(tmp_path):
    assert home(tmp_path).memory_path == tmp_path / "memory" / "summary.md"


def test_transcripts_live_in_the_home(tmp_path):
    assert home(tmp_path).transcript_dir == tmp_path / "conversation-logs"


def test_transcripts_are_kept_for_seven_days_by_default(tmp_path):
    assert home(tmp_path).memory.transcript_retention_days == 7


def test_idle_timeout_defaults_to_five_minutes(tmp_path):
    assert home(tmp_path).conversation.idle_timeout_sec == 300


def test_idle_timeout_is_set_in_minutes(tmp_path):
    cfg = home(tmp_path, "[conversation]\nidle_timeout_min = 1.5\n")
    assert cfg.conversation.idle_timeout_sec == 90


def test_non_positive_idle_timeout_is_rejected(tmp_path):
    with pytest.raises(ConfigError):
        home(tmp_path, "[conversation]\nidle_timeout_min = 0\n")


def test_unknown_setting_is_rejected(tmp_path):
    with pytest.raises(ConfigError):
        home(tmp_path, "[memory]\nmax_char = 10\n")


@pytest.mark.parametrize("section", ["personas", "speakers"])
def test_removed_sections_are_rejected(tmp_path, section):
    with pytest.raises(ConfigError, match=section):
        home(tmp_path, f"[{section}]\n")


def test_old_persona_setting_is_rejected(tmp_path):
    with pytest.raises(ConfigError, match="persona.md"):
        home(tmp_path, '[general]\npersona = "personas/child.md"\n')
