import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("app.main.get_caption_generator")
@patch("app.main.get_drive_checker")
@patch("app.main.load_last_checked")
@patch("app.main.save_last_checked")
def test_run_no_new_files(mock_save, mock_load, mock_get_drive, mock_get_caption):
    mock_load.return_value = datetime(2026, 4, 9, 0, 0, 0, tzinfo=timezone.utc)
    mock_checker = MagicMock()
    mock_checker.get_new_files.return_value = []
    mock_get_drive.return_value = mock_checker

    response = client.get("/api/run")

    assert response.status_code == 200
    data = response.json()
    assert data["files_found"] == 0
    assert data["captions_generated"] == 0


@patch("app.main.get_caption_generator")
@patch("app.main.get_drive_checker")
@patch("app.main.load_last_checked")
@patch("app.main.save_last_checked")
def test_run_with_new_files(mock_save, mock_load, mock_get_drive, mock_get_caption):
    mock_load.return_value = datetime(2026, 4, 9, 0, 0, 0, tzinfo=timezone.utc)

    mock_checker = MagicMock()
    mock_checker.get_new_files.return_value = [
        {"id": "1", "name": "post_01.png", "mimeType": "image/png", "modifiedTime": "2026-04-09T10:00:00Z"},
    ]
    mock_checker.get_text_content.return_value = "Tech launch post"
    mock_get_drive.return_value = mock_checker

    mock_generator = MagicMock()
    mock_generator.generate.return_value = {
        "instagram": "Exciting launch! 🚀",
        "linkedin": "We are thrilled to announce...",
    }
    mock_get_caption.return_value = mock_generator

    response = client.get("/api/run")

    assert response.status_code == 200
    data = response.json()
    assert data["files_found"] == 1
    assert data["captions_generated"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["file"] == "post_01.png"
    assert "instagram" in data["results"][0]["captions"]


@patch("app.main.get_caption_generator")
@patch("app.main.get_drive_checker")
@patch("app.main.load_last_checked")
@patch("app.main.save_last_checked")
def test_run_uses_filename_when_no_txt(mock_save, mock_load, mock_get_drive, mock_get_caption):
    mock_load.return_value = datetime(2026, 4, 9, 0, 0, 0, tzinfo=timezone.utc)

    mock_checker = MagicMock()
    mock_checker.get_new_files.return_value = [
        {"id": "2", "name": "sunset_photo.jpg", "mimeType": "image/jpeg", "modifiedTime": "2026-04-09T10:00:00Z"},
    ]
    mock_checker.get_text_content.return_value = None
    mock_get_drive.return_value = mock_checker

    mock_generator = MagicMock()
    mock_generator.generate.return_value = {"instagram": "x", "linkedin": "y"}
    mock_get_caption.return_value = mock_generator

    response = client.get("/api/run")

    assert response.status_code == 200
    # Verify generate was called with filename, not context
    mock_generator.generate.assert_called_once_with(context=None, filename="sunset_photo.jpg")
