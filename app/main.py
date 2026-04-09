import json
import logging
import os
from datetime import datetime, timezone

from fastapi import FastAPI

from app.config import get_drive_folder_id, get_groq_api_key
from app.services.drive_checker import DriveChecker, build_drive_service
from app.services.caption_generator import CaptionGenerator, build_groq_client

app = FastAPI(title="Social Media Posting Agent")
logger = logging.getLogger(__name__)

STATE_FILE = "state.json"


def load_last_checked() -> datetime:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            data = json.load(f)
            return datetime.fromisoformat(data["last_checked"])
    return datetime(2000, 1, 1, tzinfo=timezone.utc)


def save_last_checked(dt: datetime):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_checked": dt.isoformat()}, f)


def get_drive_checker() -> DriveChecker:
    service = build_drive_service()
    return DriveChecker(service=service, folder_id=get_drive_folder_id())


def get_caption_generator() -> CaptionGenerator:
    client = build_groq_client()
    return CaptionGenerator(client=client)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/run")
def run():
    last_checked = load_last_checked()
    checker = get_drive_checker()
    generator = get_caption_generator()

    new_files = checker.get_new_files(since=last_checked)

    if not new_files:
        logger.info("No new files found.")
        return {"files_found": 0, "captions_generated": 0, "results": []}

    results = []
    for file in new_files:
        context = checker.get_text_content(file["name"])

        if context:
            captions = generator.generate(context=context)
        else:
            captions = generator.generate(context=None, filename=file["name"])

        entry = {
            "file": file["name"],
            "file_id": file["id"],
            "captions": captions,
        }
        results.append(entry)
        logger.info("Generated captions for %s: %s", file["name"], json.dumps(captions))

    save_last_checked(datetime.now(timezone.utc))

    return {
        "files_found": len(new_files),
        "captions_generated": len(results),
        "results": results,
    }
