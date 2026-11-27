import json

from adria_harness.control import ControlInbox


def write(path, *commands, start=1):
    with path.open("a", encoding="utf-8") as f:
        for i, c in enumerate(commands, start):
            f.write(json.dumps({"seq": i, "command": c}) + "\n")


def test_no_commands_before_the_app_writes_any(tmp_path):
    assert ControlInbox(tmp_path / "control.jsonl").poll() == []


def test_new_commands_are_returned_in_order(tmp_path):
    inbox = ControlInbox(tmp_path / "control.jsonl")
    write(tmp_path / "control.jsonl", "toggle", "quit")
    assert inbox.poll() == ["toggle", "quit"]


def test_a_command_is_returned_once(tmp_path):
    inbox = ControlInbox(tmp_path / "control.jsonl")
    write(tmp_path / "control.jsonl", "toggle")
    inbox.poll()
    assert inbox.poll() == []


def test_commands_left_from_a_previous_run_are_ignored(tmp_path):
    write(tmp_path / "control.jsonl", "toggle")
    assert ControlInbox(tmp_path / "control.jsonl").poll() == []


def test_unknown_commands_are_skipped(tmp_path):
    inbox = ControlInbox(tmp_path / "control.jsonl")
    write(tmp_path / "control.jsonl", "dance", "toggle")
    assert inbox.poll() == ["toggle"]


def test_malformed_lines_are_skipped(tmp_path):
    inbox = ControlInbox(tmp_path / "control.jsonl")
    with (tmp_path / "control.jsonl").open("a") as f:
        f.write("garbage\n")
    write(tmp_path / "control.jsonl", "toggle")
    assert inbox.poll() == ["toggle"]


def test_a_partly_written_line_waits_for_its_end(tmp_path):
    inbox = ControlInbox(tmp_path / "control.jsonl")
    with (tmp_path / "control.jsonl").open("a") as f:
        f.write('{"seq": 1, "command": "tog')
    assert inbox.poll() == []


def test_a_line_is_read_once_it_is_complete(tmp_path):
    inbox = ControlInbox(tmp_path / "control.jsonl")
    path = tmp_path / "control.jsonl"
    with path.open("a") as f:
        f.write('{"seq": 1, "command": "tog')
    inbox.poll()
    with path.open("a") as f:
        f.write('gle"}\n')
    assert inbox.poll() == ["toggle"]


def test_a_truncated_file_is_read_from_the_start(tmp_path):
    path = tmp_path / "control.jsonl"
    write(path, "toggle", "toggle", "toggle")
    inbox = ControlInbox(path)
    path.write_text("")
    write(path, "quit")
    assert inbox.poll() == ["quit"]
