from datetime import datetime, timezone
import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult
from app.config import settings


class SlackPlatform(BasePlatform):
    """
    Slack Integration (Web API / Incoming Webhooks).
    Publishes a message to a designated Slack channel.
    Official Documentation: https://api.slack.com/methods/chat.postMessage
    """

    name: str = "Slack"
    public_access: bool = False  # Slack channels require workspace authentication

    def is_configured(self) -> bool:
        has_webhook = bool(settings.SLACK_WEBHOOK_URL)
        has_bot_api = bool(settings.SLACK_BOT_TOKEN and settings.SLACK_CHANNEL_ID)
        return has_webhook or has_bot_api

    async def publish(self, message: str, cta_url: str, client: httpx.AsyncClient) -> PlatformResult:
        # Case 1: Bot Token API (chat.postMessage)
        if settings.SLACK_BOT_TOKEN and settings.SLACK_CHANNEL_ID:
            url = "https://slack.com/api/chat.postMessage"
            headers = {
                "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
                "Content-Type": "application/json"
            }
            payload = {
                "channel": settings.SLACK_CHANNEL_ID,
                "text": message
            }
            response = await client.post(url, headers=headers, json=payload)
            try:
                data = response.json()
            except Exception:
                return self.create_failure_result(
                    f"Slack API error ({response.status_code}): {response.text[:200]}"
                )

            if not data.get("ok"):
                error_msg = data.get("error", "Unknown Slack API error")
                return self.create_failure_result(f"Slack API error: {error_msg}")

            channel_id = data.get("channel", settings.SLACK_CHANNEL_ID)
            ts = data.get("ts", "")
            # Convert timestamp e.g. "1731666600.000200" to "p1731666600000200"
            clean_ts = "p" + ts.replace(".", "")
            posted_url = f"https://slack.com/archives/{channel_id}/{clean_ts}"

            try:
                unix_sec = float(ts.split(".")[0])
                dt = datetime.fromtimestamp(unix_sec, tz=timezone.utc)
                date_str = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M:%S")
            except Exception:
                date_str, time_str = self.get_current_timestamp()

            return self.create_success_result(
                posted_url=posted_url,
                date_str=date_str,
                time_str=time_str
            )

        # Case 2: Incoming Webhook
        elif settings.SLACK_WEBHOOK_URL:
            webhook_url = settings.SLACK_WEBHOOK_URL
            payload = {"text": message}
            response = await client.post(webhook_url, json=payload)

            if response.status_code != 200 or response.text.strip() != "ok":
                return self.create_failure_result(
                    f"Slack Webhook error ({response.status_code}): {response.text}"
                )

            date_str, time_str = self.get_current_timestamp()
            # For incoming webhook where no permalink is returned
            posted_url = webhook_url.split("?")[0]

            return self.create_success_result(
                posted_url=posted_url,
                date_str=date_str,
                time_str=time_str
            )

        return self.create_failure_result("Authentication failed: Missing Slack credentials")

    def simulate_mock_publish(self, message: str, cta_url: str) -> PlatformResult:
        date_str, time_str = self.get_current_timestamp()
        mock_channel = settings.SLACK_CHANNEL_ID or "C08ABC12345"
        mock_ts = "p1731666600000200"
        return self.create_success_result(
            posted_url=f"https://slack.com/archives/{mock_channel}/{mock_ts}",
            date_str=date_str,
            time_str=time_str
        )
