from datetime import datetime, timezone
import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult
from app.config import settings


class BlueskyPlatform(BasePlatform):
    """
    Bluesky (AT Protocol) API Integration.
    Publishes a public post to Bluesky using XRPC endpoints.
    Official Documentation: https://docs.bsky.app/docs/api/com-atproto-repo-create-record
    """

    name: str = "Bluesky"
    public_access: bool = True

    def is_configured(self) -> bool:
        return bool(settings.BLUESKY_IDENTIFIER and settings.BLUESKY_APP_PASSWORD)

    async def publish(self, message: str, cta_url: str, client: httpx.AsyncClient) -> PlatformResult:
        pds_url = settings.BLUESKY_PDS_URL.rstrip("/")
        
        # Step 1: Create AT Protocol Session
        session_url = f"{pds_url}/xrpc/com.atproto.server.createSession"
        session_payload = {
            "identifier": settings.BLUESKY_IDENTIFIER,
            "password": settings.BLUESKY_APP_PASSWORD
        }
        session_resp = await client.post(session_url, json=session_payload)

        if session_resp.status_code != 200:
            try:
                error_detail = session_resp.json().get("message", session_resp.text[:200])
            except Exception:
                error_detail = session_resp.text[:200]
            return self.create_failure_result(f"Bluesky auth error: {error_detail}")

        try:
            session_data = session_resp.json()
        except Exception:
            return self.create_failure_result("Bluesky returned non-JSON session response")

        access_jwt = session_data.get("accessJwt")
        did = session_data.get("did")
        handle = session_data.get("handle", settings.BLUESKY_IDENTIFIER)

        # Step 2: Create Post Record
        create_record_url = f"{pds_url}/xrpc/com.atproto.repo.createRecord"
        headers = {
            "Authorization": f"Bearer {access_jwt}",
            "Content-Type": "application/json"
        }

        now_utc = datetime.now(timezone.utc)
        record_payload = {
            "repo": did,
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": message,
                "createdAt": now_utc.isoformat()
            }
        }

        record_resp = await client.post(create_record_url, headers=headers, json=record_payload)

        if record_resp.status_code not in (200, 201):
            try:
                error_detail = record_resp.json().get("message", record_resp.text[:200])
            except Exception:
                error_detail = record_resp.text[:200]
            return self.create_failure_result(f"Bluesky post error: {error_detail}")

        try:
            record_data = record_resp.json()
        except Exception:
            return self.create_failure_result("Bluesky returned non-JSON record response")
        # uri format: at://did:plc:abcdef12345/app.bsky.feed.post/3kabcde
        at_uri = record_data.get("uri", "")
        rkey = at_uri.split("/")[-1] if "/" in at_uri else "latest"
        posted_url = f"https://bsky.app/profile/{handle}/post/{rkey}"

        date_str = now_utc.strftime("%Y-%m-%d")
        time_str = now_utc.strftime("%H:%M:%S")

        return self.create_success_result(
            posted_url=posted_url,
            date_str=date_str,
            time_str=time_str
        )

    def simulate_mock_publish(self, message: str, cta_url: str) -> PlatformResult:
        date_str, time_str = self.get_current_timestamp()
        handle = settings.BLUESKY_IDENTIFIER or "demo.bsky.social"
        mock_rkey = "3lac78xyz12"
        return self.create_success_result(
            posted_url=f"https://bsky.app/profile/{handle}/post/{mock_rkey}",
            date_str=date_str,
            time_str=time_str
        )
