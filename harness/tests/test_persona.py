import pytest

from adria_harness.persona import PersonaError, load_persona, parse_persona

FULL = """+++
[voice]
reference = "kid-voice"
caption = "やさしい声"

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
    assert parse_persona("child", FULL).prompt == "# じんかく\nあなたは「テスト」です。"


def test_voice_reference_is_read():
    assert parse_persona("child", FULL).voice.reference == "kid-voice"


def test_voice_caption_is_read():
    assert parse_persona("child", FULL).voice.caption == "やさしい声"


def test_reply_sentence_limit_is_read():
    assert parse_persona("child", FULL).reply.max_sentences == 2


def test_reply_char_limit_is_read():
    assert parse_persona("child", FULL).reply.max_chars == 60


def test_memory_focus_is_read():
    assert parse_persona("child", FULL).memory.focus == ("すきなもの", "やくそく")


def test_memory_user_label_is_read():
    assert parse_persona("child", FULL).memory.user_label == "子ども"


def test_file_without_front_matter_is_all_prompt():
    assert parse_persona("child", "あなたは「テスト」です。").prompt == "あなたは「テスト」です。"


def test_voice_defaults_to_the_global_settings():
    assert parse_persona("child", "x").voice.reference is None


def test_reply_limit_has_a_default():
    assert parse_persona("child", "x").reply.max_sentences > 0


def test_unknown_key_is_rejected():
    with pytest.raises(PersonaError):
        parse_persona("child", '+++\n[voice]\nrefrence = "x"\n+++\nbody')


def test_unclosed_front_matter_is_rejected():
    with pytest.raises(PersonaError):
        parse_persona("child", '+++\n[voice]\ncaption = "x"\nbody')


def test_empty_prompt_is_rejected():
    with pytest.raises(PersonaError):
        parse_persona("child", '+++\n[reply]\nmax_sentences = 2\n+++\n\n')


def test_non_positive_limit_is_rejected():
    with pytest.raises(PersonaError):
        parse_persona("child", "+++\n[reply]\nmax_sentences = 0\n+++\nbody")


@pytest.mark.parametrize("name", ["../child", "child/x", "", ".hidden", "Child"])
def test_unsafe_names_are_rejected(tmp_path, name):
    with pytest.raises(PersonaError):
        load_persona(tmp_path, name)


def test_load_reads_the_named_file(tmp_path):
    (tmp_path / "parent.md").write_text("おとな向け", encoding="utf-8")
    assert load_persona(tmp_path, "parent").prompt == "おとな向け"


def test_load_reports_a_missing_file(tmp_path):
    with pytest.raises(PersonaError):
        load_persona(tmp_path, "nobody")
