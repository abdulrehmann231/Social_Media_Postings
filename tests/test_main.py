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
@patch("app.main.load_posted_ids")
@patch("app.main.save_posted_ids")
@patch("app.main.load_linkedin_token", return_value=None)
def test_run_no_new_files(mock_token, mock_save_ids, mock_load_ids, mock_get_drive, mock_get_caption):
    mock_load_ids.return_value = set()
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
@patch("app.main.load_posted_ids")
@patch("app.main.save_posted_ids")
def test_run_processes_first_unposted_file(mock_save_ids, mock_load_ids, mock_get_drive, mock_get_caption, mock_token, mock_poster_cls):
    mock_load_ids.return_value = set()

    mock_checker = MagicMock()
    mock_checker.get_new_files.return_value = [
        {"id": "1", "name": "post_01.png", "mimeType": "image/png", "modifiedTime": "2026-04-09T10:00:00Z"},
        {"id": "2", "name": "post_02.png", "mimeType": "image/png", "modifiedTime": "2026-04-09T11:00:00Z"},
    ]
    mock_checker.get_text_content.return_value = "Tech launch post"
    mock_checker.download_file.return_value = b"fake image bytes"
    mock_get_drive.return_value = mock_checker

    mock_generator = MagicMock()
    mock_generator.generate.return_value = {"linkedin": "We are thrilled to announce..."}
    mock_get_caption.return_value = mock_generator

    mock_poster = MagicMock()
    mock_poster.get_person_urn.return_value = "urn:li:person:abc123"
    mock_poster.upload_image.return_value = "urn:li:digitalmediaAsset:D123"
    mock_poster.create_image_post.return_value = {"id": "urn:li:share:12345"}
    mock_poster_cls.return_value = mock_poster

    response = client.get("/api/run")

    assert response.status_code == 200
    data = response.json()
    assert data["captions_generated"] == 1
    assert data["results"][0]["file"] == "post_01.png"
    assert data["results"][0]["posted_to_linkedin"] is True
    # Verify file ID "1" was saved as posted
    mock_save_ids.assert_called_once()
    saved_ids = mock_save_ids.call_args[0][0]
    assert "1" in saved_ids


@patch("app.main.LinkedInPoster")
@patch("app.main.load_linkedin_token", return_value="fake_token")
@patch("app.main.get_caption_generator")
@patch("app.main.get_drive_checker")
@patch("app.main.load_posted_ids")
@patch("app.main.save_posted_ids")
def test_run_skips_already_posted_files(mock_save_ids, mock_load_ids, mock_get_drive, mock_get_caption, mock_token, mock_poster_cls):
    # File "1" was already posted
    mock_load_ids.return_value = {"1"}

    mock_checker = MagicMock()
    mock_checker.get_new_files.return_value = [
        {"id": "1", "name": "post_01.png", "mimeType": "image/png", "modifiedTime": "2026-04-09T10:00:00Z"},
        {"id": "2", "name": "post_02.png", "mimeType": "image/png", "modifiedTime": "2026-04-09T11:00:00Z"},
    ]
    mock_checker.get_text_content.return_value = "Second post"
    mock_checker.download_file.return_value = b"image bytes"
    mock_get_drive.return_value = mock_checker

    mock_generator = MagicMock()
    mock_generator.generate.return_value = {"linkedin": "Second post caption"}
    mock_get_caption.return_value = mock_generator

    mock_poster = MagicMock()
    mock_poster.get_person_urn.return_value = "urn:li:person:abc123"
    mock_poster.upload_image.return_value = "urn:li:digitalmediaAsset:D456"
    mock_poster.create_image_post.return_value = {"id": "urn:li:share:67890"}
    mock_poster_cls.return_value = mock_poster

    response = client.get("/api/run")

    assert response.status_code == 200
    data = response.json()
    # Should process file "2", not "1"
    assert data["results"][0]["file"] == "post_02.png"
    saved_ids = mock_save_ids.call_args[0][0]
    assert "1" in saved_ids
    assert "2" in saved_ids


@patch("app.main.get_caption_generator")
@patch("app.main.get_drive_checker")
@patch("app.main.load_posted_ids")
@patch("app.main.save_posted_ids")
@patch("app.main.load_linkedin_token", return_value=None)
def test_run_all_files_already_posted(mock_token, mock_save_ids, mock_load_ids, mock_get_drive, mock_get_caption):
    mock_load_ids.return_value = {"1", "2"}

    mock_checker = MagicMock()
    mock_checker.get_new_files.return_value = [
        {"id": "1", "name": "post_01.png", "mimeType": "image/png", "modifiedTime": "2026-04-09T10:00:00Z"},
        {"id": "2", "name": "post_02.png", "mimeType": "image/png", "modifiedTime": "2026-04-09T11:00:00Z"},
    ]
    mock_get_drive.return_value = mock_checker

    response = client.get("/api/run")

    assert response.status_code == 200
    data = response.json()
    assert data["captions_generated"] == 0
    assert data["results"] == []


@patch("app.main.load_linkedin_token", return_value=None)
@patch("app.main.get_caption_generator")
@patch("app.main.get_drive_checker")
@patch("app.main.load_posted_ids")
@patch("app.main.save_posted_ids")
def test_run_skips_linkedin_when_no_token(mock_save_ids, mock_load_ids, mock_get_drive, mock_get_caption, mock_token):
    mock_load_ids.return_value = set()

    mock_checker = MagicMock()
    mock_checker.get_new_files.return_value = [
        {"id": "1", "name": "post_01.png", "mimeType": "image/png", "modifiedTime": "2026-04-09T10:00:00Z"},
    ]
    mock_checker.get_text_content.return_value = "Test post"
    mock_checker.download_file.return_value = b"image data"
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
@patch("app.main.load_posted_ids")
@patch("app.main.save_posted_ids")
def test_run_uses_filename_when_no_txt(mock_save_ids, mock_load_ids, mock_get_drive, mock_get_caption, mock_token):
    mock_load_ids.return_value = set()

    mock_checker = MagicMock()
    mock_checker.get_new_files.return_value = [
        {"id": "2", "name": "sunset_photo.jpg", "mimeType": "image/jpeg", "modifiedTime": "2026-04-09T10:00:00Z"},
    ]
    mock_checker.get_text_content.return_value = None
    mock_checker.download_file.return_value = b"sunset image"
    mock_get_drive.return_value = mock_checker

    mock_generator = MagicMock()
    mock_generator.generate.return_value = {"linkedin": "y"}
    mock_get_caption.return_value = mock_generator

    response = client.get("/api/run")

    assert response.status_code == 200
    mock_generator.generate.assert_called_once_with(image_bytes=b"sunset image", filename="sunset_photo.jpg")


def test_auth_linkedin_redirects():
    response = client.get("/auth/linkedin", follow_redirects=False)
    assert response.status_code == 307
    assert "linkedin.com/oauth/v2/authorization" in response.headers["location"]
    assert "w_member_social" in response.headers["location"]
