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
@patch("app.main.load_linkedin_token", return_value=None)
def test_run_no_new_files(mock_token, mock_save, mock_load, mock_get_drive, mock_get_caption):
    mock_load.return_value = datetime(2026, 4, 9, 0, 0, 0, tzinfo=timezone.utc)
    mock_checker = MagicMock()
    mock_checker.get_new_files.return_value = []
    mock_get_drive.return_value = mock_checker

    response = client.get("/api/run")

    assert response.status_code == 200
    data = response.json()
    assert data["files_found"] == 0
    assert data["captions_generated"] == 0


@patch("app.main.LinkedInPoster")
@patch("app.main.load_linkedin_token", return_value="fake_token")
@patch("app.main.get_caption_generator")
@patch("app.main.get_drive_checker")
@patch("app.main.load_last_checked")
@patch("app.main.save_last_checked")
def test_run_processes_only_first_file(mock_save, mock_load, mock_get_drive, mock_get_caption, mock_token, mock_poster_cls):
    mock_load.return_value = datetime(2026, 4, 9, 0, 0, 0, tzinfo=timezone.utc)

    mock_checker = MagicMock()
    mock_checker.get_new_files.return_value = [
        {"id": "1", "name": "post_01.png", "mimeType": "image/png", "modifiedTime": "2026-04-09T10:00:00Z"},
        {"id": "2", "name": "post_02.png", "mimeType": "image/png", "modifiedTime": "2026-04-09T11:00:00Z"},
    ]
    mock_checker.get_text_content.return_value = "Tech launch post"
    mock_get_drive.return_value = mock_checker

    mock_generator = MagicMock()
    mock_generator.generate.return_value = {"linkedin": "We are thrilled to announce..."}
    mock_get_caption.return_value = mock_generator

    mock_poster = MagicMock()
    mock_poster.get_person_urn.return_value = "urn:li:person:abc123"
    mock_poster.create_text_post.return_value = {"id": "urn:li:share:12345"}
    mock_poster_cls.return_value = mock_poster

    response = client.get("/api/run")

    assert response.status_code == 200
    data = response.json()
    assert data["files_found"] == 2
    assert data["captions_generated"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["file"] == "post_01.png"
    assert data["results"][0]["posted_to_linkedin"] is True


@patch("app.main.load_linkedin_token", return_value=None)
@patch("app.main.get_caption_generator")
@patch("app.main.get_drive_checker")
@patch("app.main.load_last_checked")
@patch("app.main.save_last_checked")
def test_run_skips_linkedin_when_no_token(mock_save, mock_load, mock_get_drive, mock_get_caption, mock_token):
    mock_load.return_value = datetime(2026, 4, 9, 0, 0, 0, tzinfo=timezone.utc)

    mock_checker = MagicMock()
    mock_checker.get_new_files.return_value = [
        {"id": "1", "name": "post_01.png", "mimeType": "image/png", "modifiedTime": "2026-04-09T10:00:00Z"},
    ]
    mock_checker.get_text_content.return_value = "Test post"
    mock_get_drive.return_value = mock_checker

    mock_generator = MagicMock()
    mock_generator.generate.return_value = {"linkedin": "Caption text"}
    mock_get_caption.return_value = mock_generator

    response = client.get("/api/run")

    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["posted_to_linkedin"] is False


@patch("app.main.load_linkedin_token", return_value=None)
@patch("app.main.get_caption_generator")
@patch("app.main.get_drive_checker")
@patch("app.main.load_last_checked")
@patch("app.main.save_last_checked")
def test_run_uses_filename_when_no_txt(mock_save, mock_load, mock_get_drive, mock_get_caption, mock_token):
    mock_load.return_value = datetime(2026, 4, 9, 0, 0, 0, tzinfo=timezone.utc)

    mock_checker = MagicMock()
    mock_checker.get_new_files.return_value = [
        {"id": "2", "name": "sunset_photo.jpg", "mimeType": "image/jpeg", "modifiedTime": "2026-04-09T10:00:00Z"},
    ]
    mock_checker.get_text_content.return_value = None
    mock_get_drive.return_value = mock_checker

    mock_generator = MagicMock()
    mock_generator.generate.return_value = {"linkedin": "y"}
    mock_get_caption.return_value = mock_generator

    response = client.get("/api/run")

    assert response.status_code == 200
    mock_generator.generate.assert_called_once_with(context=None, filename="sunset_photo.jpg")


def test_auth_linkedin_redirects():
    response = client.get("/auth/linkedin", follow_redirects=False)
    assert response.status_code == 307
    assert "linkedin.com/oauth/v2/authorization" in response.headers["location"]
    assert "w_member_social" in response.headers["location"]
