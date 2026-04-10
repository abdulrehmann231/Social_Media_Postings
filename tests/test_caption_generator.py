import json
import base64
from unittest.mock import MagicMock

from app.services.caption_generator import CaptionGenerator, SYSTEM_PROMPT, VISION_MODEL


def _mock_groq_response(content: str):
    """Create a mock Groq chat completion response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    return mock_response


class TestGenerate:
    def test_returns_linkedin_caption_with_image_and_context(self):
        mock_client = MagicMock()
        caption = {"linkedin": "Excited to announce our latest product at Sofject."}
        mock_client.chat.completions.create.return_value = _mock_groq_response(json.dumps(caption))

        generator = CaptionGenerator(client=mock_client)
        result = generator.generate(images=[b"fake png"], context="New product launch")

        assert "linkedin" in result
        assert "instagram" not in result

    def test_sends_image_as_base64_in_message(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            json.dumps({"linkedin": "caption"})
        )

        image_data = b"fake image bytes"
        generator = CaptionGenerator(client=mock_client)
        generator.generate(images=[image_data], context="Test post")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        user_msg = messages[-1]["content"]
        # Should be a list with text + image_url parts
        assert isinstance(user_msg, list)
        types = [part["type"] for part in user_msg]
        assert "text" in types
        assert "image_url" in types
        # Verify base64 encoding
        image_part = [p for p in user_msg if p["type"] == "image_url"][0]
        expected_b64 = base64.b64encode(image_data).decode()
        assert expected_b64 in image_part["image_url"]["url"]

    def test_sends_all_images_as_separate_parts(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            json.dumps({"linkedin": "caption"})
        )

        pages = [b"page 1 bytes", b"page 2 bytes", b"page 3 bytes"]
        generator = CaptionGenerator(client=mock_client)
        generator.generate(images=pages, context="Carousel about X")

        call_args = mock_client.chat.completions.create.call_args
        user_content = call_args[1]["messages"][-1]["content"]
        image_parts = [p for p in user_content if p["type"] == "image_url"]
        assert len(image_parts) == 3
        for page_bytes, part in zip(pages, image_parts):
            expected = base64.b64encode(page_bytes).decode()
            assert expected in part["image_url"]["url"]

    def test_raises_when_images_empty(self):
        mock_client = MagicMock()
        generator = CaptionGenerator(client=mock_client)
        try:
            generator.generate(images=[], context="test")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "at least one image" in str(e).lower()

    def test_uses_vision_model(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            json.dumps({"linkedin": "y"})
        )

        generator = CaptionGenerator(client=mock_client)
        generator.generate(images=[b"img"], context="test")

        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == VISION_MODEL

    def test_includes_context_in_text_part(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            json.dumps({"linkedin": "y"})
        )

        generator = CaptionGenerator(client=mock_client)
        generator.generate(images=[b"img"], context="Sofject new office launch")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        user_content = messages[-1]["content"]
        text_part = [p for p in user_content if p["type"] == "text"][0]
        assert "Sofject new office launch" in text_part["text"]

    def test_text_mentions_carousel_when_multiple_images(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            json.dumps({"linkedin": "y"})
        )

        generator = CaptionGenerator(client=mock_client)
        generator.generate(images=[b"p1", b"p2", b"p3"], context="Launch")

        call_args = mock_client.chat.completions.create.call_args
        text_part = [
            p for p in call_args[1]["messages"][-1]["content"] if p["type"] == "text"
        ][0]
        # Prompt should tell the model it's a multi-slide carousel with 3 slides
        assert "3" in text_part["text"]
        assert "carousel" in text_part["text"].lower() or "slides" in text_part["text"].lower()

    def test_uses_filename_when_no_context(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            json.dumps({"linkedin": "y"})
        )

        generator = CaptionGenerator(client=mock_client)
        generator.generate(images=[b"img"], filename="team_event.png")

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        user_content = messages[-1]["content"]
        text_part = [p for p in user_content if p["type"] == "text"][0]
        assert "team_event.png" in text_part["text"]

    def test_handles_json_in_markdown_code_block(self):
        mock_client = MagicMock()
        raw = '```json\n{"linkedin": "Hi there from Sofject."}\n```'
        mock_client.chat.completions.create.return_value = _mock_groq_response(raw)

        generator = CaptionGenerator(client=mock_client)
        result = generator.generate(images=[b"img"], context="test")

        assert result["linkedin"] == "Hi there from Sofject."

    def test_raises_on_invalid_response(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_groq_response("not json at all")

        generator = CaptionGenerator(client=mock_client)
        try:
            generator.generate(images=[b"img"], context="test")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Failed to parse" in str(e)

    def test_system_prompt_mentions_sofject(self):
        assert "Sofject" in SYSTEM_PROMPT
        assert "sofject.com" in SYSTEM_PROMPT
