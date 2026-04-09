import json
import os
import re

from groq import Groq

DEFAULT_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a social media manager. Generate two captions for a post.

Platform 1: Instagram (casual, emoji, hashtags, max 2200 chars)
Platform 2: LinkedIn (professional, insightful, no hashtags in body, max 3000 chars)

Return ONLY valid JSON with this exact structure:
{"instagram": "caption here", "linkedin": "caption here"}"""


def build_groq_client() -> Groq:
    return Groq(api_key=os.environ["GROQ_API_KEY"])


class CaptionGenerator:
    def __init__(self, client: Groq = None, model: str = DEFAULT_MODEL):
        self.client = client
        self.model = model

    def generate(self, context: str | None = None, filename: str | None = None) -> dict:
        if context:
            user_msg = f"Topic/Context: {context}"
        elif filename:
            user_msg = f"Generate captions based on this image filename: {filename}"
        else:
            user_msg = "Generate generic social media captions for a new post."

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
        )

        raw = response.choices[0].message.content
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> dict:
        # Strip markdown code blocks if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse caption response: {raw[:200]}")

        return {"instagram": data["instagram"], "linkedin": data["linkedin"]}
