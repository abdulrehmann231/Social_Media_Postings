import json
import logging
import os
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.config import (
    get_drive_unposted_folder_id,
    get_drive_posted_folder_id,
    get_groq_api_key,
    get_linkedin_client_id,
    get_linkedin_client_secret,
    get_linkedin_redirect_uri,
    get_linkedin_access_token,
)
from app.services.drive_checker import DriveChecker, build_drive_service, is_pdf
from app.services.caption_generator import CaptionGenerator, build_groq_client
from app.services.caption_log import append_caption_log
from app.services.linkedin_poster import LinkedInPoster, exchange_code_for_token
from app.services.pdf_utils import pdf_first_page_to_png

app = FastAPI(title="Social Media Posting Agent")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TOKEN_FILE = "linkedin_token.json"


def load_linkedin_token() -> str | None:
    """Load LinkedIn token from file, falling back to env var."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            data = json.load(f)
            return data.get("access_token")
    return get_linkedin_access_token()


def save_linkedin_token(token_data: dict):
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)


def get_drive_checker() -> DriveChecker:
    service = build_drive_service()
    return DriveChecker(service=service, folder_id=get_drive_unposted_folder_id())


def get_caption_generator() -> CaptionGenerator:
    client = build_groq_client()
    return CaptionGenerator(client=client)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/auth/linkedin")
def auth_linkedin():
    """Redirect user to LinkedIn OAuth authorization page."""
    params = urlencode({
        "response_type": "code",
        "client_id": get_linkedin_client_id(),
        "redirect_uri": get_linkedin_redirect_uri(),
        "scope": "openid profile w_member_social",
    })
    return RedirectResponse(f"https://www.linkedin.com/oauth/v2/authorization?{params}")


@app.get("/auth/linkedin/callback")
def auth_linkedin_callback(code: str):
    """Exchange OAuth code for access token and store it."""
    token_data = exchange_code_for_token(
        code=code,
        client_id=get_linkedin_client_id(),
        client_secret=get_linkedin_client_secret(),
        redirect_uri=get_linkedin_redirect_uri(),
    )
    save_linkedin_token(token_data)
    logger.info("LinkedIn token saved successfully.")
    return {
        "status": "ok",
        "message": "LinkedIn token saved. Copy access_token into the LINKEDIN_ACCESS_TOKEN env var to survive redeploys.",
        "access_token": token_data.get("access_token"),
        "expires_in": token_data.get("expires_in"),
    }


@app.get("/api/run")
def run():
    checker = get_drive_checker()
    generator = get_caption_generator()
    posted_folder_id = get_drive_posted_folder_id()

    # Get files from the unposted folder
    unposted_files = checker.get_files()

    if not unposted_files:
        logger.info("No unposted files found.")
        return {"files_found": 0, "captions_generated": 0, "results": []}

    # Process only the first file
    file = unposted_files[0]
    file_bytes = checker.download_file(file["id"])
    file_is_pdf = is_pdf(file)
    context = checker.get_text_content(file["name"])

    # For PDFs, convert first page to PNG for the vision model
    vision_image = pdf_first_page_to_png(file_bytes) if file_is_pdf else file_bytes

    if context:
        captions = generator.generate(image_bytes=vision_image, context=context)
    else:
        captions = generator.generate(image_bytes=vision_image, filename=file["name"])

    entry = {
        "file": file["name"],
        "file_id": file["id"],
        "captions": captions,
        "posted_to_linkedin": False,
    }

    # Post to LinkedIn if token is available
    token = load_linkedin_token()
    if token:
        try:
            poster = LinkedInPoster(access_token=token)
            person_urn = poster.get_person_urn()
            if file_is_pdf:
                doc_urn = poster.upload_document(person_urn=person_urn, pdf_bytes=file_bytes)
                poster.create_document_post(person_urn=person_urn, text=captions["linkedin"], document_urn=doc_urn)
            else:
                image_asset = poster.upload_image(person_urn=person_urn, image_bytes=file_bytes)
                poster.create_image_post(person_urn=person_urn, text=captions["linkedin"], image_asset=image_asset)
            entry["posted_to_linkedin"] = True
            logger.info("Posted to LinkedIn: %s", file["name"])
        except Exception as e:
            logger.error("Failed to post to LinkedIn: %s", str(e))
            entry["linkedin_error"] = str(e)
    else:
        logger.warning("No LinkedIn token — skipping post. Visit /auth/linkedin to authorize.")

    logger.info("Generated captions for %s: %s", file["name"], json.dumps(captions))

    append_caption_log({
        "file": file["name"],
        "file_id": file["id"],
        "captions": captions,
        "posted_to_linkedin": entry["posted_to_linkedin"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Only move the file to the posted folder if LinkedIn actually accepted it.
    if entry["posted_to_linkedin"]:
        checker.move_file(file_id=file["id"], dest_folder_id=posted_folder_id)
        logger.info("Moved %s to posted folder.", file["name"])
    else:
        logger.info("Leaving %s in unposted folder (post did not succeed).", file["name"])

    return {
        "files_found": len(unposted_files),
        "captions_generated": 1,
        "results": [entry],
    }
