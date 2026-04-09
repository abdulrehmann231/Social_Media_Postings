import json
import os
import re

from groq import Groq

DEFAULT_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are the social media manager for Sofject, a software house.
Website: sofject.com

Generate a professional LinkedIn caption for this post.
- Professional, insightful tone
- Highlight Sofject's expertise in software development
- No hashtags in the body, add 3-5 relevant hashtags at the end
- Max 3000 characters
- Do NOT use generic filler — be specific to the context provided

Return ONLY valid JSON with this exact structure:
{"linkedin": "caption here"}"""


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
            user_msg = f"Generate a caption based on this image filename: {filename}"
        else:
            user_msg = "Generate a LinkedIn caption for a new post from Sofject."

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

        return {"linkedin": data["linkedin"]}
