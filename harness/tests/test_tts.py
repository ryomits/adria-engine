from adria_harness.config import TTSConfig
from adria_harness.tts import request_body

CFG = TTSConfig(voice="adria", caption="あかるい声", num_steps=16, seed=42)


def test_configured_voice_is_used():
    assert request_body(CFG, "やあ")["voice"] == "adria"


def test_configured_caption_is_used():
    assert request_body(CFG, "やあ")["irodori"]["caption"] == "あかるい声"


def test_text_is_sent_as_input():
    assert request_body(CFG, "やあ")["input"] == "やあ"


def test_seed_is_passed_through():
    assert request_body(CFG, "やあ")["irodori"]["seed"] == 42
