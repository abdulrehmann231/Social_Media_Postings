import json
from unittest.mock import MagicMock, patch, call

import pytest

from app.services.linkedin_poster import LinkedInPoster


class TestGetUserProfile:
    def test_returns_person_urn(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sub": "abc123"}

        poster = LinkedInPoster(access_token="fake_token")
        with patch("app.services.linkedin_poster.httpx.get", return_value=mock_response):
            urn = poster.get_person_urn()

        assert urn == "urn:li:person:abc123"

    def test_raises_on_failed_profile_fetch(self):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")

        poster = LinkedInPoster(access_token="bad_token")
        with patch("app.services.linkedin_poster.httpx.get", return_value=mock_response):
            with pytest.raises(Exception):
                poster.get_person_urn()


class TestUploadImage:
    def test_registers_upload_and_uploads_bytes(self):
        # Step 1: Register upload returns upload URL and asset
        register_response = MagicMock()
        register_response.status_code = 200
        register_response.json.return_value = {
            "value": {
                "uploadMechanism": {
                    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest": {
                        "uploadUrl": "https://api.linkedin.com/mediaUpload/xxx"
                    }
                },
                "asset": "urn:li:digitalmediaAsset:D123456",
            }
        }

        # Step 2: Upload image bytes returns 201
        upload_response = MagicMock()
        upload_response.status_code = 201

        poster = LinkedInPoster(access_token="fake_token")
        with patch("app.services.linkedin_poster.httpx.post", side_effect=[register_response, upload_response]) as mock_post:
            with patch("app.services.linkedin_poster.httpx.put", return_value=upload_response) as mock_put:
                asset_urn = poster.upload_image(
                    person_urn="urn:li:person:abc123",
                    image_bytes=b"fake image data",
                )

        assert asset_urn == "urn:li:digitalmediaAsset:D123456"
        # Verify register was called
        register_call = mock_post.call_args
        body = register_call[1]["json"]
        assert body["registerUploadRequest"]["owner"] == "urn:li:person:abc123"
        # Verify image bytes were uploaded via PUT
        mock_put.assert_called_once()

    def test_raises_on_failed_register(self):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = Exception("403")

        poster = LinkedInPoster(access_token="fake_token")
        with patch("app.services.linkedin_poster.httpx.post", return_value=mock_response):
            with pytest.raises(Exception):
                poster.upload_image("urn:li:person:abc", b"data")


class TestCreateImagePost:
    def test_creates_post_with_image(self):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "urn:li:share:99999"}

        poster = LinkedInPoster(access_token="fake_token")
        with patch("app.services.linkedin_poster.httpx.post", return_value=mock_response) as mock_post:
            result = poster.create_image_post(
                person_urn="urn:li:person:abc123",
                text="Check out this post!",
                image_asset="urn:li:digitalmediaAsset:D123456",
            )

        assert result["id"] == "urn:li:share:99999"
        body = mock_post.call_args[1]["json"]
        assert body["author"] == "urn:li:person:abc123"
        media_content = body["specificContent"]["com.linkedin.ugc.ShareContent"]
        assert media_content["shareMediaCategory"] == "IMAGE"
        assert media_content["shareCommentary"]["text"] == "Check out this post!"
        assert media_content["media"][0]["media"] == "urn:li:digitalmediaAsset:D123456"

    def test_raises_on_failed_image_post(self):
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.raise_for_status.side_effect = Exception("422")

        poster = LinkedInPoster(access_token="fake_token")
        with patch("app.services.linkedin_poster.httpx.post", return_value=mock_response):
            with pytest.raises(Exception):
                poster.create_image_post(
                    person_urn="urn:li:person:abc",
                    text="Test",
                    image_asset="urn:li:digitalmediaAsset:D1",
                )


class TestCreateTextPost:
    def test_posts_text_successfully(self):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "urn:li:share:12345"}

        poster = LinkedInPoster(access_token="fake_token")
        with patch("app.services.linkedin_poster.httpx.post", return_value=mock_response):
            result = poster.create_text_post(
                person_urn="urn:li:person:abc123",
                text="Hello from Sofject!",
            )

        assert result["id"] == "urn:li:share:12345"


class TestExchangeCodeForToken:
    def test_returns_access_token(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token_123",
            "expires_in": 5184000,
        }

        with patch("app.services.linkedin_poster.httpx.post", return_value=mock_response):
            from app.services.linkedin_poster import exchange_code_for_token
            result = exchange_code_for_token(
                code="auth_code_abc",
                client_id="test_id",
                client_secret="test_secret",
                redirect_uri="https://example.com/callback",
            )

        assert result["access_token"] == "new_token_123"
