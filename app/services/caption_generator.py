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


def _image_mime(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
        return "image/gif"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    # Many Drive sources (JFIF, unknown) still decode as JPEG; default to it.
    return "image/jpeg"


class CaptionGenerator:
    def __init__(self, client: Groq = None, model: str = VISION_MODEL):
        self.client = client
        self.model = model

    def generate(
        self,
        images: list[bytes],
        context: str | None = None,
        filename: str | None = None,
    ) -> dict:
        if not images:
            raise ValueError("generate() requires at least one image")

        is_carousel = len(images) > 1
        if is_carousel:
            lead = (
                f"This is a {len(images)}-slide LinkedIn carousel. "
                "Review every slide and write one caption that reflects the full "
                "narrative across all slides, not just the cover."
            )
        else:
            lead = "Generate a LinkedIn caption for this image from Sofject."

        if context:
            text = f"{lead}\nTopic/Context: {context}"
        elif filename:
            text = f"{lead}\nFilename: {filename}"
        else:
            text = lead

        user_content: list[dict] = [{"type": "text", "text": text}]
        for img_bytes in images:
            b64_image = base64.b64encode(img_bytes).decode()
            mime = _image_mime(img_bytes)
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64_image}"},
                }
            )

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
