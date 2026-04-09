import os
import base64
import json

from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials


IMAGE_MIME_TYPES = ("image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp")
SCOPES = ["https://www.googleapis.com/auth/drive"]


def build_drive_service():
    """Build a Google Drive API service from the base64-encoded service account key in env."""
    raw = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    info = json.loads(base64.b64decode(raw))
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


class DriveChecker:
    def __init__(self, service, folder_id: str):
        self.service = service
        self.folder_id = folder_id

    def get_images(self) -> list[dict]:
        """List all image files in the folder."""
        mime_filter = " or ".join(f"mimeType='{m}'" for m in IMAGE_MIME_TYPES)
        q = f"'{self.folder_id}' in parents and ({mime_filter}) and trashed=false"

        response = self.service.files().list(
            q=q,
            fields="files(id, name, mimeType)",
            orderBy="createdTime",
        ).execute()

        return response.get("files", [])

    def download_file(self, file_id: str) -> bytes:
        """Download a file's content by its ID."""
        return self.service.files().get_media(fileId=file_id).execute()

    def get_text_content(self, image_filename: str) -> str | None:
        """Look for a companion .txt file with the same base name and return its content."""
        base_name = os.path.splitext(image_filename)[0]
        txt_name = f"{base_name}.txt"

        response = self.service.files().list(
            q=f"'{self.folder_id}' in parents and name='{txt_name}' and trashed=false",
            fields="files(id, name)",
        ).execute()

        files = response.get("files", [])
        if not files:
            return None

        content_bytes = self.service.files().get_media(fileId=files[0]["id"]).execute()
        return content_bytes.decode("utf-8")

    def move_file(self, file_id: str, dest_folder_id: str) -> dict:
        """Move a file from this folder to the destination folder."""
        return self.service.files().update(
            fileId=file_id,
            addParents=dest_folder_id,
            removeParents=self.folder_id,
            fields="id, parents",
        ).execute()
