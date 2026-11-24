import datetime as dt
import json
import stat

from adria_harness.transcript import TranscriptLog

NOW = dt.datetime(2026, 11, 25, 10, 0, 0)


def entry():
    return {"persona": "child", "speaker": None, "user": "いちごすき", "reply": "おいしいよね。"}


def test_turn_is_written_to_the_file_of_the_day(tmp_path):
    TranscriptLog(tmp_path, retention_days=7).append(entry(), now=NOW)
    line = (tmp_path / "2026-11-25.jsonl").read_text(encoding="utf-8").strip()
    assert json.loads(line)["user"] == "いちごすき"


def test_turn_is_timestamped(tmp_path):
    TranscriptLog(tmp_path, retention_days=7).append(entry(), now=NOW)
    line = (tmp_path / "2026-11-25.jsonl").read_text(encoding="utf-8").strip()
    assert json.loads(line)["at"] == "2026-11-25T10:00:00"


def test_log_file_is_readable_by_the_owner_only(tmp_path):
    TranscriptLog(tmp_path, retention_days=7).append(entry(), now=NOW)
    mode = stat.S_IMODE((tmp_path / "2026-11-25.jsonl").stat().st_mode)
    assert mode == 0o600


def test_files_older_than_the_retention_are_deleted(tmp_path):
    (tmp_path / "2026-11-18.jsonl").write_text("{}\n")
    TranscriptLog(tmp_path, retention_days=7).purge(now=NOW)
    assert not (tmp_path / "2026-11-18.jsonl").exists()


def test_files_within_the_retention_are_kept(tmp_path):
    (tmp_path / "2026-11-19.jsonl").write_text("{}\n")
    TranscriptLog(tmp_path, retention_days=7).purge(now=NOW)
    assert (tmp_path / "2026-11-19.jsonl").exists()


def test_unrelated_files_are_left_alone(tmp_path):
    (tmp_path / "notes.txt").write_text("x")
    TranscriptLog(tmp_path, retention_days=7).purge(now=NOW)
    assert (tmp_path / "notes.txt").exists()


def test_appending_purges_old_files(tmp_path):
    (tmp_path / "2026-11-01.jsonl").write_text("{}\n")
    TranscriptLog(tmp_path, retention_days=7).append(entry(), now=NOW)
    assert not (tmp_path / "2026-11-01.jsonl").exists()


def test_the_log_offers_no_way_to_read_it_back():
    # Full transcripts are for parents only; nothing in the harness reads them.
    assert not [n for n in dir(TranscriptLog) if not n.startswith("_")
                and n not in ("append", "purge")]
