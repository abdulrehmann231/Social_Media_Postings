from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.services.drive_checker import DriveChecker


def _make_file_entry(file_id, name, mime_type="image/png"):
    return {"id": file_id, "name": name, "mimeType": mime_type}


class TestGetImages:
    def test_returns_image_files_in_folder(self):
        mock_service = MagicMock()
        files = [
            _make_file_entry("1", "post_01.png"),
            _make_file_entry("2", "post_02.jpg", mime_type="image/jpeg"),
        ]
        mock_service.files().list().execute.return_value = {"files": files}

        checker = DriveChecker(service=mock_service, folder_id="test_folder")
        result = checker.get_images()

        assert len(result) == 2
        assert result[0]["name"] == "post_01.png"
        assert result[1]["name"] == "post_02.jpg"

    def test_returns_empty_list_when_no_files(self):
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {"files": []}

        checker = DriveChecker(service=mock_service, folder_id="test_folder")
        result = checker.get_images()

        assert result == []

    def test_queries_correct_folder(self):
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {"files": []}

        checker = DriveChecker(service=mock_service, folder_id="abc123")
        checker.get_images()

        call_kwargs = mock_service.files().list.call_args[1]
        assert "'abc123' in parents" in call_kwargs["q"]


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


class TestMoveFile:
    def test_moves_file_to_destination_folder(self):
        mock_service = MagicMock()
        mock_service.files().update().execute.return_value = {"id": "file_1"}

        checker = DriveChecker(service=mock_service, folder_id="source_folder")
        checker.move_file(file_id="file_1", dest_folder_id="dest_folder")

        mock_service.files().update.assert_called_with(
            fileId="file_1",
            addParents="dest_folder",
            removeParents="source_folder",
            fields="id, parents",
        )

    def test_move_returns_updated_file(self):
        mock_service = MagicMock()
        mock_service.files().update().execute.return_value = {"id": "file_1", "parents": ["dest"]}

        checker = DriveChecker(service=mock_service, folder_id="source_folder")
        result = checker.move_file(file_id="file_1", dest_folder_id="dest_folder")

        assert result["id"] == "file_1"
