import os
from dotenv import load_dotenv

load_dotenv()


def get_drive_folder_id() -> str:
    return os.environ["DRIVE_FOLDER_ID"]


def get_groq_api_key() -> str:
    return os.environ["GROQ_API_KEY"]
