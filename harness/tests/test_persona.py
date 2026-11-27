import pytest

from adria_harness.persona import PersonaError, load_persona, parse_persona

FULL = """+++
[reply]
max_sentences = 2
max_chars = 60

[memory]
user_label = "子ども"
focus = ["すきなもの", "やくそく"]
+++
# じんかく
あなたは「テスト」です。
"""


def test_body_becomes_the_prompt():
    assert parse_persona(FULL).prompt == "# じんかく\nあなたは「テスト」です。"


def test_reply_sentence_limit_is_read():
    assert parse_persona(FULL).reply.max_sentences == 2


def test_reply_char_limit_is_read():
    assert parse_persona(FULL).reply.max_chars == 60


def test_memory_focus_is_read():
    assert parse_persona(FULL).memory.focus == ("すきなもの", "やくそく")


def test_memory_user_label_is_read():
    assert parse_persona(FULL).memory.user_label == "子ども"


def test_file_without_front_matter_is_all_prompt():
    assert parse_persona("あなたは「テスト」です。").prompt == "あなたは「テスト」です。"


def test_reply_limit_has_a_default():
    assert parse_persona("x").reply.max_sentences > 0


def test_unknown_key_is_rejected():
    with pytest.raises(PersonaError):
        parse_persona("+++\n[reply]\nmax_sentence = 2\n+++\nbody")


def test_voice_section_is_rejected():
    # The voice is set once in config.toml [tts]; a persona can no longer override it.
    with pytest.raises(PersonaError):
        parse_persona('+++\n[voice]\ncaption = "x"\n+++\nbody')


def test_unclosed_front_matter_is_rejected():
    with pytest.raises(PersonaError):
        parse_persona("+++\n[reply]\nmax_sentences = 2\nbody")


def test_empty_prompt_is_rejected():
    with pytest.raises(PersonaError):
        parse_persona("+++\n[reply]\nmax_sentences = 2\n+++\n\n")


def test_non_positive_limit_is_rejected():
    with pytest.raises(PersonaError):
        parse_persona("+++\n[reply]\nmax_sentences = 0\n+++\nbody")


def test_load_reads_the_file(tmp_path):
    (tmp_path / "persona.md").write_text("こども向け", encoding="utf-8")
    assert load_persona(tmp_path / "persona.md").prompt == "こども向け"


def test_load_reports_a_missing_file(tmp_path):
    with pytest.raises(PersonaError):
        load_persona(tmp_path / "persona.md")
