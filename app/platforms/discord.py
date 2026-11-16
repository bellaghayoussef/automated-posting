from datetime import datetime
from typing import Optional
import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult
from app.config import settings


class DiscordPlatform(BasePlatform):
    """
    Discord Webhook API Integration.
    Publishes a message to a Discord text channel.
    Official Documentation: https://discord.com/developers/docs/resources/webhook#execute-webhook
    """

    name: str = "Discord"
    public_access: bool = False  # Discord channels require authentication & server membership

    def is_configured(self) -> bool:
        return bool(settings.DISCORD_WEBHOOK_URL)

    async def publish(self, message: str, cta_url: str, client: httpx.AsyncClient) -> PlatformResult:
        webhook_url = settings.DISCORD_WEBHOOK_URL

        # Ensure ?wait=true parameter is present so Discord returns the created message JSON
        separator = "&" if "?" in webhook_url else "?"
        url_with_wait = f"{webhook_url}{separator}wait=true"

        payload = {
            "content": message
        }

        response = await client.post(url_with_wait, json=payload)

        if response.status_code not in (200, 204):
            return self.create_failure_result(
                f"Discord API error ({response.status_code}): {response.text[:200]}"
            )

        # Discord returns message payload when wait=true
        if response.status_code == 200:
            try:
                data = response.json()
            except Exception:
                return self.create_failure_result("Discord API returned non-JSON response")
            message_id = data.get("id")
            channel_id = data.get("channel_id")
            guild_id = data.get("guild_id", "@me")
            iso_timestamp = data.get("timestamp")

            posted_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"

            if iso_timestamp:
                try:
                    dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
                    date_str = dt.strftime("%Y-%m-%d")
                    time_str = dt.strftime("%H:%M:%S")
                except Exception:
                    date_str, time_str = self.get_current_timestamp()
            else:
                date_str, time_str = self.get_current_timestamp()
        else:
            # Fallback for 204 No Content
            posted_url = webhook_url.split("?")[0]
            date_str, time_str = self.get_current_timestamp()

        return self.create_success_result(
            posted_url=posted_url,
            date_str=date_str,
            time_str=time_str
        )

    def simulate_mock_publish(self, message: str, cta_url: str) -> PlatformResult:
        date_str, time_str = self.get_current_timestamp()
        mock_guild_id = "1198765432109876543"
        mock_channel_id = "1098765432109876543"
        mock_msg_id = "1287654321098765432"
        return self.create_success_result(
            posted_url=f"https://discord.com/channels/{mock_guild_id}/{mock_channel_id}/{mock_msg_id}",
            date_str=date_str,
            time_str=time_str
        )
