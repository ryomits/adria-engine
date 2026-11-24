import pytest

from adria_harness.config import ConfigError, load_config


def home(tmp_path, toml=""):
    (tmp_path / "config.toml").write_text(toml, encoding="utf-8")
    return load_config(tmp_path)


def test_default_persona_is_child(tmp_path):
    assert home(tmp_path).default_persona == "child"


def test_default_persona_can_be_set(tmp_path):
    assert home(tmp_path, '[personas]\ndefault = "kid"\n').default_persona == "kid"


def test_personas_live_in_the_home(tmp_path):
    assert home(tmp_path).persona_dir == tmp_path / "personas"


def test_memory_lives_in_the_home(tmp_path):
    assert home(tmp_path).memory_dir == tmp_path / "memory"


def test_transcripts_live_in_the_home(tmp_path):
    assert home(tmp_path).transcript_dir == tmp_path / "conversation-logs"


def test_transcripts_are_kept_for_seven_days_by_default(tmp_path):
    assert home(tmp_path).memory.transcript_retention_days == 7


def test_speaker_map_is_read(tmp_path):
    cfg = home(tmp_path, '[speakers.map]\nmom = "parent"\n')
    assert cfg.speakers.map == {"mom": "parent"}


def test_voiceprints_default_to_the_home(tmp_path):
    assert home(tmp_path).speakers.voiceprint_dir == tmp_path / "voiceprints"


def test_relative_voiceprint_dir_is_resolved_against_the_home(tmp_path):
    cfg = home(tmp_path, '[speakers]\nvoiceprint_dir = "vp"\n')
    assert cfg.speakers.voiceprint_dir == tmp_path / "vp"


def test_unknown_speaker_setting_is_rejected(tmp_path):
    with pytest.raises(ConfigError):
        home(tmp_path, "[speakers]\nthreshhold = 0.5\n")


def test_old_persona_setting_points_to_the_new_one(tmp_path):
    with pytest.raises(ConfigError, match="personas"):
        home(tmp_path, '[general]\npersona = "personas/child.md"\n')
