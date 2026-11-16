from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables and .env file.
    """
    # Application settings
    APP_NAME: str = "Automated Multi-Platform Posting System"
    APP_PORT: int = 4000
    APP_HOST: str = "0.0.0.0"
    DEBUG: bool = False
    REQUEST_TIMEOUT: float = 15.0

    # Demo / Simulation Mode:
    # When True, platforms simulate successful API responses if real credentials are not provided.
    # When False, unconfigured platforms return "status: failed" with authentication errors.
    MOCK_MODE: bool = False

    # 1. Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # 2. Discord
    DISCORD_WEBHOOK_URL: Optional[str] = None

    # 3. Slack (supports incoming webhook or Bot Token + Channel)
    SLACK_WEBHOOK_URL: Optional[str] = None
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_CHANNEL_ID: Optional[str] = None

    # 4. Mastodon
    MASTODON_INSTANCE_URL: str = "https://mastodon.social"
    MASTODON_ACCESS_TOKEN: Optional[str] = None

    # 5. Bluesky (AT Protocol)
    BLUESKY_IDENTIFIER: Optional[str] = None
    BLUESKY_APP_PASSWORD: Optional[str] = None
    BLUESKY_PDS_URL: str = "https://bsky.social"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

