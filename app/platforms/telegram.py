from datetime import datetime, timezone
import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult
from app.config import settings


class TelegramPlatform(BasePlatform):
    """
    Telegram Bot API Integration.
    Publishes message to a public Telegram channel or supergroup.
    Official Documentation: https://core.telegram.org/bots/api#sendmessage
    """

    name: str = "Telegram"
    public_access: bool = True

    def is_configured(self) -> bool:
        return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)

    async def publish(self, message: str, cta_url: str, client: httpx.AsyncClient) -> PlatformResult:
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_CHAT_ID
        url = f"https://api.telegram.org/bot{token}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": False
        }

        response = await client.post(url, json=payload)

        if response.status_code != 200:
            try:
                error_msg = response.json().get("description", response.text[:200])
            except Exception:
                error_msg = response.text[:200]
            return self.create_failure_result(f"Telegram API error ({response.status_code}): {error_msg}")

        try:
            data = response.json()
        except Exception:
            return self.create_failure_result("Telegram API returned non-JSON response")

        if not data.get("ok"):
            return self.create_failure_result(f"Telegram error: {data.get('description', 'Unknown error')}")

        result_obj = data.get("result", {})
        message_id = result_obj.get("message_id")
        chat_obj = result_obj.get("chat", {})
        chat_username = chat_obj.get("username")

        # Determine public posted URL
        if chat_username:
            posted_url = f"https://t.me/{chat_username}/{message_id}"
        elif str(chat_id).startswith("@"):
            posted_url = f"https://t.me/{str(chat_id).lstrip('@')}/{message_id}"
        else:
            clean_id = str(chat_id).replace("-100", "").replace("-", "")
            posted_url = f"https://t.me/c/{clean_id}/{message_id}"

        # Parse API timestamp
        unix_ts = result_obj.get("date")
        if unix_ts:
            dt = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M:%S")
        else:
            date_str, time_str = self.get_current_timestamp()

        return self.create_success_result(
            posted_url=posted_url,
            date_str=date_str,
            time_str=time_str
        )

    def simulate_mock_publish(self, message: str, cta_url: str) -> PlatformResult:
        date_str, time_str = self.get_current_timestamp()
        mock_id = "84920"
        channel = settings.TELEGRAM_CHAT_ID or "telegram_broadcast"
        channel_name = channel.lstrip("@")
        return self.create_success_result(
            posted_url=f"https://t.me/{channel_name}/{mock_id}",
            date_str=date_str,
            time_str=time_str
        )
