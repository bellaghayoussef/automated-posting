from datetime import datetime
import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult
from app.config import settings


class MastodonPlatform(BasePlatform):
    """
    Mastodon Decentralized Social Network API Integration.
    Publishes a public status (toot) across the ActivityPub fediverse.
    Official Documentation: https://docs.joinmastodon.org/methods/statuses/#create
    """

    name: str = "Mastodon"
    public_access: bool = True

    def is_configured(self) -> bool:
        return bool(settings.MASTODON_ACCESS_TOKEN and settings.MASTODON_INSTANCE_URL)

    async def publish(self, message: str, cta_url: str, client: httpx.AsyncClient) -> PlatformResult:
        instance = settings.MASTODON_INSTANCE_URL.rstrip("/")
        url = f"{instance}/api/v1/statuses"

        headers = {
            "Authorization": f"Bearer {settings.MASTODON_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "status": message,
            "visibility": "public"
        }

        response = await client.post(url, headers=headers, json=payload)

        if response.status_code not in (200, 201):
            try:
                err_data = response.json()
                err_text = err_data.get("error", response.text[:200])
            except Exception:
                err_text = response.text[:200]
            return self.create_failure_result(
                f"Mastodon API error ({response.status_code}): {err_text}"
            )

        try:
            data = response.json()
        except Exception:
            return self.create_failure_result("Mastodon API returned non-JSON response")
        
        posted_url = data.get("url") or f"{instance}/@status/{data.get('id')}"
        created_at_raw = data.get("created_at")

        if created_at_raw:
            try:
                dt = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M:%S")
            except Exception:
                date_str, time_str = self.get_current_timestamp()
        else:
            date_str, time_str = self.get_current_timestamp()

        return self.create_success_result(
            posted_url=posted_url,
            date_str=date_str,
            time_str=time_str
        )

    def simulate_mock_publish(self, message: str, cta_url: str) -> PlatformResult:
        date_str, time_str = self.get_current_timestamp()
        instance = settings.MASTODON_INSTANCE_URL.rstrip("/")
        mock_id = "113456789012345678"
        return self.create_success_result(
            posted_url=f"{instance}/@testuser/{mock_id}",
            date_str=date_str,
            time_str=time_str
        )
