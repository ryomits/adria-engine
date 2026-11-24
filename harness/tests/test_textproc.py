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


def test_limit_stops_after_max_sentences():
    from adria_harness.textproc import limit_reply
    assert list(limit_reply(iter(["あ。", "い。", "う。"]), max_sentences=2, max_chars=100)) == [
        "あ。", "い。"]


def test_limit_stops_before_exceeding_max_chars():
    from adria_harness.textproc import limit_reply
    assert list(limit_reply(iter(["あいう。", "えおか。"]), max_sentences=5, max_chars=6)) == [
        "あいう。"]


def test_limit_keeps_a_long_first_sentence():
    from adria_harness.textproc import limit_reply
    assert list(limit_reply(iter(["ながいぶんしょう。"]), max_sentences=5, max_chars=3)) == [
        "ながいぶんしょう。"]


def test_limit_does_not_read_past_the_cut():
    from adria_harness.textproc import limit_reply
    seen = []

    def source():
        for s in ["あ。", "い。", "う。"]:
            seen.append(s)
            yield s

    list(limit_reply(source(), max_sentences=1, max_chars=100))
    assert seen == ["あ。"]
