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


@patch("app.main.get_drive_posted_folder_id", return_value="posted_folder")
@patch("app.main.get_caption_generator")
@patch("app.main.get_drive_checker")
@patch("app.main.load_linkedin_token", return_value=None)
def test_run_no_unposted_files(mock_token, mock_get_drive, mock_get_caption, mock_posted_id):
    mock_checker = MagicMock()
    mock_checker.get_files.return_value = []
    mock_get_drive.return_value = mock_checker

    response = client.get("/api/run")

    assert response.status_code == 200
    data = response.json()
    assert data["files_found"] == 0
    assert data["captions_generated"] == 0


@patch("app.main.get_drive_posted_folder_id", return_value="posted_folder")
@patch("app.main.get_linkedin_organization_id", return_value="104361510")
@patch("app.main.LinkedInPoster")
@patch("app.main.load_linkedin_token", return_value="fake_token")
@patch("app.main.get_caption_generator")
@patch("app.main.get_drive_checker")
def test_run_posts_and_moves_to_posted(mock_get_drive, mock_get_caption, mock_token, mock_poster_cls, mock_org_id, mock_posted_id):
    mock_checker = MagicMock()
    mock_checker.get_files.return_value = [
        {"id": "1", "name": "post_01.png", "mimeType": "image/png"},
        {"id": "2", "name": "post_02.png", "mimeType": "image/png"},
    ]
    mock_checker.get_text_content.return_value = "Tech launch"
    mock_checker.download_file.return_value = b"fake image bytes"
    mock_get_drive.return_value = mock_checker

    mock_generator = MagicMock()
    mock_generator.generate.return_value = {"linkedin": "Caption here"}
    mock_get_caption.return_value = mock_generator

    mock_poster = MagicMock()
    mock_poster.upload_image.return_value = "urn:li:digitalmediaAsset:D123"
    mock_poster.create_image_post.return_value = {"id": "urn:li:share:12345"}
    mock_poster_cls.return_value = mock_poster

    response = client.get("/api/run")

    assert response.status_code == 200
    data = response.json()
    assert data["files_found"] == 2
    assert data["captions_generated"] == 1
    assert data["results"][0]["file"] == "post_01.png"
    assert data["results"][0]["posted_to_linkedin"] is True
    # Should post as the organization, not the personal profile
    mock_poster.get_person_urn.assert_not_called()
    mock_poster.upload_image.assert_called_once_with(
        person_urn="urn:li:organization:104361510",
        image_bytes=b"fake image bytes",
    )
    mock_poster.create_image_post.assert_called_once_with(
        person_urn="urn:li:organization:104361510",
        text="Caption here",
        image_asset="urn:li:digitalmediaAsset:D123",
    )
    # Verify file was moved to posted folder
    mock_checker.move_file.assert_called_once_with(file_id="1", dest_folder_id="posted_folder")


@patch("app.main.get_drive_posted_folder_id", return_value="posted_folder")
@patch("app.main.load_linkedin_token", return_value=None)
@patch("app.main.get_caption_generator")
@patch("app.main.get_drive_checker")
def test_run_moves_even_without_linkedin(mock_get_drive, mock_get_caption, mock_token, mock_posted_id):
    mock_checker = MagicMock()
    mock_checker.get_files.return_value = [
        {"id": "1", "name": "post_01.png", "mimeType": "image/png"},
    ]
    mock_checker.get_text_content.return_value = "Test"
    mock_checker.download_file.return_value = b"image data"
    mock_get_drive.return_value = mock_checker

    mock_generator = MagicMock()
    mock_generator.generate.return_value = {"linkedin": "Caption"}
    mock_get_caption.return_value = mock_generator

    response = client.get("/api/run")

    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["posted_to_linkedin"] is False
    # File should still be moved to posted folder
    mock_checker.move_file.assert_called_once_with(file_id="1", dest_folder_id="posted_folder")


@patch("app.main.get_drive_posted_folder_id", return_value="posted_folder")
@patch("app.main.load_linkedin_token", return_value=None)
@patch("app.main.get_caption_generator")
@patch("app.main.get_drive_checker")
def test_run_uses_filename_when_no_txt(mock_get_drive, mock_get_caption, mock_token, mock_posted_id):
    mock_checker = MagicMock()
    mock_checker.get_files.return_value = [
        {"id": "2", "name": "sunset_photo.jpg", "mimeType": "image/jpeg"},
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


@patch("app.main.pdf_first_page_to_png", return_value=b"fake png from pdf")
@patch("app.main.get_drive_posted_folder_id", return_value="posted_folder")
@patch("app.main.get_linkedin_organization_id", return_value="104361510")
@patch("app.main.LinkedInPoster")
@patch("app.main.load_linkedin_token", return_value="fake_token")
@patch("app.main.get_caption_generator")
@patch("app.main.get_drive_checker")
def test_run_pdf_creates_carousel_post(mock_get_drive, mock_get_caption, mock_token, mock_poster_cls, mock_org_id, mock_posted_id, mock_pdf_to_png):
    mock_checker = MagicMock()
    mock_checker.get_files.return_value = [
        {"id": "10", "name": "slides.pdf", "mimeType": "application/pdf"},
    ]
    mock_checker.get_text_content.return_value = "Our new deck"
    mock_checker.download_file.return_value = b"fake pdf bytes"
    mock_get_drive.return_value = mock_checker

    mock_generator = MagicMock()
    mock_generator.generate.return_value = {"linkedin": "Check out our carousel!"}
    mock_get_caption.return_value = mock_generator

    mock_poster = MagicMock()
    mock_poster.upload_document.return_value = "urn:li:document:D789"
    mock_poster.create_document_post.return_value = {"id": "urn:li:share:carousel1"}
    mock_poster_cls.return_value = mock_poster

    response = client.get("/api/run")

    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["posted_to_linkedin"] is True
    # Should convert PDF first page to PNG for vision model
    mock_pdf_to_png.assert_called_once_with(b"fake pdf bytes")
    # Caption generator should receive the PNG, not the raw PDF
    mock_generator.generate.assert_called_once_with(image_bytes=b"fake png from pdf", context="Our new deck")
    # Should use document upload + document post (not image), authored by the org
    mock_poster.get_person_urn.assert_not_called()
    mock_poster.upload_document.assert_called_once_with(
        person_urn="urn:li:organization:104361510",
        pdf_bytes=b"fake pdf bytes",
    )
    mock_poster.create_document_post.assert_called_once_with(
        person_urn="urn:li:organization:104361510",
        text="Check out our carousel!",
        document_urn="urn:li:document:D789",
    )
    # Should NOT call image upload
    mock_poster.upload_image.assert_not_called()
    mock_checker.move_file.assert_called_once_with(file_id="10", dest_folder_id="posted_folder")


def test_auth_linkedin_redirects():
    response = client.get("/auth/linkedin", follow_redirects=False)
    assert response.status_code == 307
    assert "linkedin.com/oauth/v2/authorization" in response.headers["location"]
    assert "w_member_social" in response.headers["location"]
    assert "w_organization_social" in response.headers["location"]
    assert "r_organization_social" in response.headers["location"]
