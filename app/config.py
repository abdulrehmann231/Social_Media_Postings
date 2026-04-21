import os
from dotenv import load_dotenv

load_dotenv()


def get_drive_unposted_folder_id() -> str:
    return os.environ["DRIVE_UNPOSTED_FOLDER_ID"]


def get_drive_posted_folder_id() -> str:
    return os.environ["DRIVE_POSTED_FOLDER_ID"]


def get_groq_api_key() -> str:
    return os.environ["GROQ_API_KEY"]


def get_linkedin_client_id() -> str:
    return os.environ["LINKEDIN_CLIENT_ID"]


def get_linkedin_client_secret() -> str:
    return os.environ["LINKEDIN_CLIENT_SECRET"]


def get_linkedin_redirect_uri() -> str:
    return os.environ["LINKEDIN_REDIRECT_URI"]


def get_linkedin_access_token() -> str | None:
    return os.environ.get("LINKEDIN_ACCESS_TOKEN") or None


def get_linkedin_organization_urn() -> str:
    org_id = os.environ["LINKEDIN_ORGANIZATION_ID"]
    return f"urn:li:organization:{org_id}"
