import json
from unittest.mock import MagicMock

from app.services.caption_generator import CaptionGenerator


def _mock_groq_response(content: str):
    """Create a mock Groq chat completion response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    return mock_response


class TestGenerate:
    def test_returns_captions_with_context(self):
        mock_client = MagicMock()
        captions = {"instagram": "Check out our new launch! 🚀", "linkedin": "Excited to announce our latest product."}
        mock_client.chat.completions.create.return_value = _mock_groq_response(json.dumps(captions))

        generator = CaptionGenerator(client=mock_client)
        result = generator.generate(context="New product launch for tech startup")

        assert result["instagram"] == captions["instagram"]
        assert result["linkedin"] == captions["linkedin"]

    def test_returns_captions_without_context(self):
        mock_client = MagicMock()
        captions = {"instagram": "Amazing post! #photo", "linkedin": "Sharing this update."}
        mock_client.chat.completions.create.return_value = _mock_groq_response(json.dumps(captions))

        generator = CaptionGenerator(client=mock_client)
        result = generator.generate(context=None, filename="weekend_vibes.png")

        assert "instagram" in result
        assert "linkedin" in result
        # Verify the prompt includes filename when no context
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        user_msg = messages[-1]["content"]
        assert "weekend_vibes.png" in user_msg

    def test_sends_correct_model(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            json.dumps({"instagram": "x", "linkedin": "y"})
        )

        generator = CaptionGenerator(client=mock_client, model="llama-3.3-70b-versatile")
        generator.generate(context="test")

        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "llama-3.3-70b-versatile"

    def test_handles_json_in_markdown_code_block(self):
        mock_client = MagicMock()
        raw = '```json\n{"instagram": "Hello!", "linkedin": "Hi there."}\n```'
        mock_client.chat.completions.create.return_value = _mock_groq_response(raw)

        generator = CaptionGenerator(client=mock_client)
        result = generator.generate(context="test")

        assert result["instagram"] == "Hello!"
        assert result["linkedin"] == "Hi there."

    def test_raises_on_invalid_response(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_groq_response("not json at all")

        generator = CaptionGenerator(client=mock_client)
        try:
            generator.generate(context="test")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Failed to parse" in str(e)
