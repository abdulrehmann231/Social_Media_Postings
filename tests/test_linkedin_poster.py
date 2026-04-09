import json
from unittest.mock import MagicMock, patch

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

    def test_sends_correct_payload(self):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "urn:li:share:12345"}

        poster = LinkedInPoster(access_token="fake_token")
        with patch("app.services.linkedin_poster.httpx.post", return_value=mock_response) as mock_post:
            poster.create_text_post(
                person_urn="urn:li:person:abc123",
                text="Test caption",
            )

        call_kwargs = mock_post.call_args
        body = call_kwargs[1]["json"]
        assert body["author"] == "urn:li:person:abc123"
        assert body["specificContent"]["com.linkedin.ugc.ShareContent"]["shareCommentary"]["text"] == "Test caption"

    def test_raises_on_failed_post(self):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.raise_for_status.side_effect = Exception("403 Forbidden")

        poster = LinkedInPoster(access_token="fake_token")
        with patch("app.services.linkedin_poster.httpx.post", return_value=mock_response):
            with pytest.raises(Exception):
                poster.create_text_post(
                    person_urn="urn:li:person:abc123",
                    text="Test",
                )


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
