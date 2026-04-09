import base64
import json
import os
import re

from groq import Groq

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

SYSTEM_PROMPT = """You are the social media manager for Sofject, a software house.
Website: sofject.com

Look at the provided image and generate a professional LinkedIn caption for this post.
- Professional, insightful tone
- Describe what you see in the image and relate it to Sofject's expertise in software development
- No hashtags in the body, add 3-5 relevant hashtags at the end
- Max 3000 characters
- Do NOT use generic filler — be specific to the image and context provided

Return ONLY valid JSON with this exact structure:
{"linkedin": "caption here"}"""


def build_groq_client() -> Groq:
    return Groq(api_key=os.environ["GROQ_API_KEY"])


class CaptionGenerator:
    def __init__(self, client: Groq = None, model: str = VISION_MODEL):
        self.client = client
        self.model = model

    def generate(self, image_bytes: bytes, context: str | None = None, filename: str | None = None) -> dict:
        if context:
            text = f"Topic/Context: {context}"
        elif filename:
            text = f"Generate a caption based on this image. Filename: {filename}"
        else:
            text = "Generate a LinkedIn caption for this image from Sofject."

        b64_image = base64.b64encode(image_bytes).decode()

        user_content = [
            {"type": "text", "text": text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64_image}"},
            },
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.7,
        )

        raw = response.choices[0].message.content
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse caption response: {raw[:200]}")

        return {"linkedin": data["linkedin"]}
