from adria_harness.textproc import split_sentences


def run(chunks):
    return list(split_sentences(chunks))


def test_basic_split():
    assert run(["こんにちは！アド", "リアだよ。いっしょに", "あそぼ"]) == [
        "こんにちは！", "アドリアだよ。", "いっしょにあそぼ"]


def test_trailing_marks_absorbed():
    assert run(["ほんと！？", "すごいね〜。", "うん"]) == ["ほんと！？", "すごいね〜。", "うん"]


def test_short_fragment_merged():
    assert run(["！", "わあ。", "ね"]) == ["！わあ。", "ね"]


def test_strip_markdown_and_emoji():
    assert run(["**いちご**🍓だよ。"]) == ["いちごだよ。"]
