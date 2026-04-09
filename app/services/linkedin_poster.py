import httpx

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"


def exchange_code_for_token(
    code: str, client_id: str, client_secret: str, redirect_uri: str
) -> dict:
    """Exchange an OAuth authorization code for an access token."""
    response = httpx.post(
        LINKEDIN_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        },
    )
    response.raise_for_status()
    return response.json()


class LinkedInPoster:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def get_person_urn(self) -> str:
        """Fetch the authenticated user's LinkedIn person URN."""
        response = httpx.get(LINKEDIN_USERINFO_URL, headers=self.headers)
        response.raise_for_status()
        sub = response.json()["sub"]
        return f"urn:li:person:{sub}"

    def upload_image(self, person_urn: str, image_bytes: bytes) -> str:
        """Upload an image to LinkedIn and return the asset URN."""
        # Step 1: Register the upload
        register_payload = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": person_urn,
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent",
                    }
                ],
            }
        }

        response = httpx.post(
            f"{LINKEDIN_API_BASE}/assets?action=registerUpload",
            headers=self.headers,
            json=register_payload,
        )
        response.raise_for_status()

        data = response.json()["value"]
        upload_url = data["uploadMechanism"][
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
        ]["uploadUrl"]
        asset_urn = data["asset"]

        # Step 2: Upload the image bytes
        upload_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/octet-stream",
        }
        upload_response = httpx.put(upload_url, headers=upload_headers, content=image_bytes)
        upload_response.raise_for_status()

        return asset_urn

    def create_image_post(self, person_urn: str, text: str, image_asset: str) -> dict:
        """Create a post with an image on LinkedIn."""
        payload = {
            "author": person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "IMAGE",
                    "media": [
                        {
                            "status": "READY",
                            "media": image_asset,
                        }
                    ],
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        }

        response = httpx.post(
            f"{LINKEDIN_API_BASE}/ugcPosts",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def create_text_post(self, person_urn: str, text: str) -> dict:
        """Create a text-only post on LinkedIn."""
        payload = {
            "author": person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        }

        response = httpx.post(
            f"{LINKEDIN_API_BASE}/ugcPosts",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()
