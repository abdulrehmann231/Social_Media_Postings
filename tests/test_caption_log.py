import json
import os
import tempfile
from datetime import datetime, timezone

from app.services.caption_log import append_caption_log, read_caption_log


class TestCaptionLog:
    def test_append_creates_file_if_not_exists(self, tmp_path):
        log_file = tmp_path / "captions.jsonl"
        entry = {
            "file": "post_01.png",
            "captions": {"instagram": "Hello!", "linkedin": "Greetings."},
            "timestamp": "2026-04-09T10:00:00+00:00",
        }

        append_caption_log(entry, log_path=str(log_file))

        assert log_file.exists()
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1
        assert json.loads(lines[0])["file"] == "post_01.png"

    def test_append_adds_to_existing_file(self, tmp_path):
        log_file = tmp_path / "captions.jsonl"
        entry1 = {"file": "post_01.png", "captions": {}, "timestamp": "2026-04-09T10:00:00+00:00"}
        entry2 = {"file": "post_02.png", "captions": {}, "timestamp": "2026-04-09T11:00:00+00:00"}

        append_caption_log(entry1, log_path=str(log_file))
        append_caption_log(entry2, log_path=str(log_file))

        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_read_returns_all_entries(self, tmp_path):
        log_file = tmp_path / "captions.jsonl"
        entry1 = {"file": "a.png", "captions": {}, "timestamp": "t1"}
        entry2 = {"file": "b.png", "captions": {}, "timestamp": "t2"}
        log_file.write_text(json.dumps(entry1) + "\n" + json.dumps(entry2) + "\n")

        entries = read_caption_log(log_path=str(log_file))

        assert len(entries) == 2
        assert entries[0]["file"] == "a.png"
        assert entries[1]["file"] == "b.png"

    def test_read_returns_empty_if_no_file(self, tmp_path):
        log_file = tmp_path / "nonexistent.jsonl"

        entries = read_caption_log(log_path=str(log_file))

        assert entries == []
