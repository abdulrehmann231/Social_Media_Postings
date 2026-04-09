from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.services.drive_checker import DriveChecker


def _make_file_entry(file_id, name, mime_type="image/png", modified_time="2026-04-09T10:00:00.000Z"):
    return {"id": file_id, "name": name, "mimeType": mime_type, "modifiedTime": modified_time}


class TestGetNewFiles:
    def test_returns_image_files_modified_after_since(self):
        mock_service = MagicMock()
        files = [
            _make_file_entry("1", "post_01.png"),
            _make_file_entry("2", "post_02.jpg", mime_type="image/jpeg"),
        ]
        mock_service.files().list().execute.return_value = {"files": files}

        checker = DriveChecker(service=mock_service, folder_id="test_folder")
        since = datetime(2026, 4, 9, 0, 0, 0, tzinfo=timezone.utc)
        result = checker.get_new_files(since)

        assert len(result) == 2
        assert result[0]["name"] == "post_01.png"
        assert result[1]["name"] == "post_02.jpg"

    def test_returns_empty_list_when_no_files(self):
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {"files": []}

        checker = DriveChecker(service=mock_service, folder_id="test_folder")
        since = datetime(2026, 4, 9, 0, 0, 0, tzinfo=timezone.utc)
        result = checker.get_new_files(since)

        assert result == []

    def test_passes_correct_query_with_folder_and_time(self):
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {"files": []}

        checker = DriveChecker(service=mock_service, folder_id="abc123")
        since = datetime(2026, 4, 9, 8, 30, 0, tzinfo=timezone.utc)
        checker.get_new_files(since)

        call_kwargs = mock_service.files().list.call_args[1]
        assert "abc123" in call_kwargs["q"]
        assert "2026-04-09T08:30:00" in call_kwargs["q"]


class TestDownloadFile:
    def test_downloads_file_bytes(self):
        mock_service = MagicMock()
        mock_request = MagicMock()
        mock_request.execute.return_value = b"fake image bytes"
        mock_service.files().get_media.return_value = mock_request

        checker = DriveChecker(service=mock_service, folder_id="test_folder")
        result = checker.download_file("file_123")

        assert result == b"fake image bytes"
        mock_service.files().get_media.assert_called_with(fileId="file_123")


class TestGetTextContent:
    def test_returns_text_for_companion_file(self):
        mock_service = MagicMock()
        # Simulate finding a companion .txt file
        mock_service.files().list().execute.return_value = {
            "files": [{"id": "txt_1", "name": "post_01.txt"}]
        }
        mock_request = MagicMock()
        mock_request.execute.return_value = b"Tech startup launch post"
        mock_service.files().get_media.return_value = mock_request

        checker = DriveChecker(service=mock_service, folder_id="test_folder")
        result = checker.get_text_content("post_01.png")

        assert result == "Tech startup launch post"

    def test_returns_none_when_no_companion_file(self):
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {"files": []}

        checker = DriveChecker(service=mock_service, folder_id="test_folder")
        result = checker.get_text_content("post_01.png")

        assert result is None
