import json
from unittest.mock import MagicMock

from app.services.caption_generator import CaptionGenerator, SYSTEM_PROMPT


def _mock_groq_response(content: str):
    """Create a mock Groq chat completion response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    return mock_response


class TestGenerate:
    def test_returns_linkedin_caption_with_context(self):
        mock_client = MagicMock()
        caption = {"linkedin": "Excited to announce our latest product at Sofject."}
        mock_client.chat.completions.create.return_value = _mock_groq_response(json.dumps(caption))

        generator = CaptionGenerator(client=mock_client)
        result = generator.generate(context="New product launch")

        assert "linkedin" in result
        assert "instagram" not in result

    def test_returns_linkedin_caption_without_context(self):
        mock_client = MagicMock()
        caption = {"linkedin": "Sharing this update from Sofject."}
        mock_client.chat.completions.create.return_value = _mock_groq_response(json.dumps(caption))

        generator = CaptionGenerator(client=mock_client)
        result = generator.generate(context=None, filename="weekend_vibes.png")

        assert "linkedin" in result
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        user_msg = messages[-1]["content"]
        assert "weekend_vibes.png" in user_msg

    def test_sends_correct_model(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_groq_response(
            json.dumps({"linkedin": "y"})
        )

        generator = CaptionGenerator(client=mock_client, model="llama-3.3-70b-versatile")
        generator.generate(context="test")

        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "llama-3.3-70b-versatile"

    def test_handles_json_in_markdown_code_block(self):
        mock_client = MagicMock()
        raw = '```json\n{"linkedin": "Hi there from Sofject."}\n```'
        mock_client.chat.completions.create.return_value = _mock_groq_response(raw)

        generator = CaptionGenerator(client=mock_client)
        result = generator.generate(context="test")

        assert result["linkedin"] == "Hi there from Sofject."

    def test_raises_on_invalid_response(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _mock_groq_response("not json at all")

        generator = CaptionGenerator(client=mock_client)
        try:
            generator.generate(context="test")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Failed to parse" in str(e)

    def test_system_prompt_mentions_sofject(self):
        assert "Sofject" in SYSTEM_PROMPT
        assert "sofject.com" in SYSTEM_PROMPT

    def test_system_prompt_is_linkedin_only(self):
        assert "Instagram" not in SYSTEM_PROMPT
        assert "instagram" not in SYSTEM_PROMPT.lower() or "linkedin" in SYSTEM_PROMPT.lower()
