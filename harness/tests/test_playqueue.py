from adria_harness.playqueue import PlayQueue, tts_fields


def test_fifo_and_atomic_file(tmp_path):
    q = PlayQueue(tmp_path)
    q.push({"id": "a", "text": "1"}, {"id": "b", "text": "2"})
    lines = (tmp_path / "queue.jsonl").read_text().splitlines()
    assert len(lines) == 2
    assert q.pop()["id"] == "a"
    assert q.pop()["id"] == "b"
    assert q.pop() is None
    assert not (tmp_path / "queue.jsonl.part").exists()


def test_x_keys_stripped():
    item = {"text": "やあ", "x_expression": "happy", "x_motion": "wave"}
    assert tts_fields(item) == {"text": "やあ"}
