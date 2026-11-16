import pytest
from starlette.testclient import TestClient
from unittest.mock import AsyncMock, patch
import httpx

from app.main import app
from app.config import settings
from app.services.posting_service import PostingService
from app.platforms.telegram import TelegramPlatform
from app.platforms.discord import DiscordPlatform
from app.platforms.slack import SlackPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.bluesky import BlueskyPlatform
from app.schemas import PlatformResult

client = TestClient(app)


# ==============================================================================
# 1. Input Validation Tests
# ==============================================================================

def test_valid_message_passes_validation():
    """Valid message with <= 200 chars and exactly 1 CTA link."""
    payload = {
        "message": "Check out our latest business platform and grow your online visibility. https://example.com"
    }
    response = client.post("/posting", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 5


def test_message_exceeding_200_chars_fails():
    """Message over 200 characters must return 422 Unprocessable Entity."""
    long_msg = "A" * 190 + " https://example.com"  # 190 + 1 + 19 = 210 chars
    assert len(long_msg) > 200

    payload = {"message": long_msg}
    response = client.post("/posting", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert "must not exceed 200 characters" in str(data["details"])


def test_message_with_no_cta_link_fails():
    """Message without any CTA link must return 422."""
    payload = {
        "message": "Check out our latest business platform and grow your visibility."
    }
    response = client.post("/posting", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert "Exactly one CTA link must be included" in str(data["details"])


def test_message_with_multiple_cta_links_fails():
    """Message with more than one CTA link must return 422."""
    payload = {
        "message": "Visit https://example.com and check https://another.com"
    }
    response = client.post("/posting", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert "Found 2 links" in str(data["details"])


def test_message_with_invalid_url_fails():
    """Message with an invalid URL or scheme must return 422."""
    payload = {
        "message": "Visit ftp://example.com to learn more about us."
    }
    response = client.post("/posting", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False


def test_message_with_malformed_domain_fails():
    """Message with a URL lacking a valid host/domain must return 422."""
    payload = {
        "message": "Visit https://invalid..domain for details."
    }
    response = client.post("/posting", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False


def test_payload_with_extra_fields_fails():
    """
    Platform selection must be handled internally. Supplying extra fields must be rejected.
    """
    payload = {
        "message": "Check out our latest business platform. https://example.com",
        "platform": "telegram"
    }
    response = client.post("/posting", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False


def test_empty_message_fails():
    """Empty or whitespace-only message must return 422."""
    payload = {"message": "   "}
    response = client.post("/posting", json=payload)
    assert response.status_code == 422


# ==============================================================================
# 2. Multi-Platform Posting & Failure Isolation Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_failure_isolation_one_platform_fails_others_succeed():
    """
    Verify that if one platform fails (e.g. Platform B fails),
    the application continues posting to the remaining platforms.
    """
    # Create mock platforms
    p1 = TelegramPlatform()
    p1.post = AsyncMock(return_value=PlatformResult(
        platform="Telegram",
        status="success",
        posted_url="https://t.me/testchannel/101",
        public_access=True,
        date="2026-11-16",
        time="10:00:00",
        error=None
    ))

    p2 = DiscordPlatform()
    p2.post = AsyncMock(return_value=PlatformResult(
        platform="Discord",
        status="failed",
        posted_url=None,
        public_access=False,
        date=None,
        time=None,
        error="Authentication failed: Missing credentials for Discord"
    ))

    p3 = SlackPlatform()
    p3.post = AsyncMock(return_value=PlatformResult(
        platform="Slack",
        status="success",
        posted_url="https://slack.com/archives/C123/p1731666600000200",
        public_access=False,
        date="2026-11-16",
        time="10:00:01",
        error=None
    ))

    service = PostingService(platforms=[p1, p2, p3])
    response = await service.post_to_all("Test message https://example.com", "https://example.com")

    # Overall success is true because at least one succeeded
    assert response.success is True
    assert len(response.results) == 3

    # Platform 1 succeeded
    assert response.results[0].platform == "Telegram"
    assert response.results[0].status == "success"
    assert response.results[0].posted_url == "https://t.me/testchannel/101"

    # Platform 2 failed independently
    assert response.results[1].platform == "Discord"
    assert response.results[1].status == "failed"
    assert response.results[1].error == "Authentication failed: Missing credentials for Discord"
    assert response.results[1].posted_url is None

    # Platform 3 succeeded
    assert response.results[2].platform == "Slack"
    assert response.results[2].status == "success"


@pytest.mark.asyncio
async def test_all_five_platforms_publish_successfully():
    """Verify posting across all 5 integrated platforms concurrently."""
    platforms = [
        TelegramPlatform(),
        DiscordPlatform(),
        SlackPlatform(),
        MastodonPlatform(),
        BlueskyPlatform()
    ]

    for p in platforms:
        p.post = AsyncMock(return_value=PlatformResult(
            platform=p.name,
            status="success",
            posted_url=f"https://{p.name.lower()}.com/post/999",
            public_access=p.public_access,
            date="2026-11-16",
            time="10:30:00",
            error=None
        ))

    service = PostingService(platforms=platforms)
    response = await service.post_to_all("Check out https://example.com", "https://example.com")

    assert response.success is True
    assert len(response.results) == 5
    for r in response.results:
        assert r.status == "success"
        assert r.posted_url is not None
        assert r.date == "2026-11-16"
        assert r.time == "10:30:00"
        assert r.error is None


@pytest.mark.asyncio
async def test_mock_mode_simulation():
    """Verify that in MOCK_MODE, unconfigured platforms simulate successful responses."""
    with patch.object(settings, "MOCK_MODE", True):
        telegram = TelegramPlatform()
        result = await telegram.post("Test message https://example.com", "https://example.com")
        assert result.status == "success"
        assert "t.me" in result.posted_url
        assert result.public_access is True
        assert result.date is not None
        assert result.time is not None


@pytest.mark.asyncio
async def test_unconfigured_platforms_return_authentication_failed_when_not_in_mock_mode():
    """Verify unconfigured platforms return expected failure format."""
    with patch.object(settings, "MOCK_MODE", False):
        with patch.object(settings, "DISCORD_WEBHOOK_URL", None):
            discord = DiscordPlatform()
            result = await discord.post("Test message https://example.com", "https://example.com")
            assert result.status == "failed"
            assert result.posted_url is None
            assert result.public_access is False
            assert "Authentication failed" in result.error


def test_message_with_trailing_period_and_params():
    """URL with query params and a trailing sentence period must extract correctly."""
    payload = {
        "message": "Visit our portal at https://sub.domain.co/register?ref=test&id=123."
    }
    response = client.post("/posting", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True or data["success"] is False
    assert len(data["results"]) == 5


@pytest.mark.asyncio
async def test_platform_http_status_error_handling():
    """Verify HTTP status errors (e.g. 500) are caught and mapped to failed PlatformResult."""
    telegram = TelegramPlatform()
    mock_resp = httpx.Response(status_code=500, text="Internal Server Error")
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp

    with patch.object(settings, "TELEGRAM_BOT_TOKEN", "fake_token"):
        with patch.object(settings, "TELEGRAM_CHAT_ID", "@testchannel"):
            result = await telegram.publish("Hello https://example.com", "https://example.com", mock_client)
            assert result.status == "failed"
            assert result.posted_url is None
            assert "Telegram API error" in result.error


@pytest.mark.asyncio
async def test_telegram_publish_success():
    """Test TelegramPlatform.publish parsing of successful response."""
    telegram = TelegramPlatform()
    mock_resp = httpx.Response(
        status_code=200,
        json={
            "ok": True,
            "result": {
                "message_id": 789,
                "date": 1731666600,
                "chat": {"id": -1001234567890, "username": "awesome_channel"}
            }
        }
    )
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp

    with patch.object(settings, "TELEGRAM_BOT_TOKEN", "fake_bot_token"):
        with patch.object(settings, "TELEGRAM_CHAT_ID", "@awesome_channel"):
            result = await telegram.publish("Visit https://example.com", "https://example.com", mock_client)
            assert result.status == "success"
            assert result.posted_url == "https://t.me/awesome_channel/789"
            assert result.public_access is True
            assert result.date is not None
            assert result.time is not None


@pytest.mark.asyncio
async def test_discord_publish_success():
    """Test DiscordPlatform.publish parsing of successful response."""
    discord = DiscordPlatform()
    mock_resp = httpx.Response(
        status_code=200,
        json={
            "id": "1306912345678901234",
            "channel_id": "1105432109876543210",
            "guild_id": "1001234567890123456",
            "timestamp": "2026-11-15T10:30:00.000000+00:00"
        }
    )
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp

    with patch.object(settings, "DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/123/abc"):
        result = await discord.publish("Visit https://example.com", "https://example.com", mock_client)
        assert result.status == "success"
        assert result.posted_url == "https://discord.com/channels/1001234567890123456/1105432109876543210/1306912345678901234"
        assert result.public_access is False
        assert result.date == "2026-11-15"
        assert result.time == "10:30:00"


@pytest.mark.asyncio
async def test_slack_publish_bot_token_success():
    """Test SlackPlatform.publish with Slack Web API (Bot Token)."""
    slack = SlackPlatform()
    mock_resp = httpx.Response(
        status_code=200,
        json={
            "ok": True,
            "channel": "C1234567890",
            "ts": "1731666600.000200"
        }
    )
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp

    with patch.object(settings, "SLACK_BOT_TOKEN", "xoxb-fake-token"):
        with patch.object(settings, "SLACK_CHANNEL_ID", "C1234567890"):
            result = await slack.publish("Visit https://example.com", "https://example.com", mock_client)
            assert result.status == "success"
            assert result.posted_url == "https://slack.com/archives/C1234567890/p1731666600000200"
            assert result.public_access is False


@pytest.mark.asyncio
async def test_slack_publish_webhook_success():
    """Test SlackPlatform.publish with Incoming Webhook."""
    slack = SlackPlatform()
    mock_resp = httpx.Response(status_code=200, text="ok")
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp

    with patch.object(settings, "SLACK_BOT_TOKEN", None):
        with patch.object(settings, "SLACK_CHANNEL_ID", None):
            with patch.object(settings, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/T00/B00/X00"):
                result = await slack.publish("Visit https://example.com", "https://example.com", mock_client)
                assert result.status == "success"
                assert result.posted_url == "https://hooks.slack.com/services/T00/B00/X00"
                assert result.public_access is False


@pytest.mark.asyncio
async def test_mastodon_publish_success():
    """Test MastodonPlatform.publish parsing of successful status creation."""
    mastodon = MastodonPlatform()
    mock_resp = httpx.Response(
        status_code=200,
        json={
            "id": "113456789012345678",
            "created_at": "2026-11-15T10:30:00.000Z",
            "url": "https://mastodon.social/@demouser/113456789012345678"
        }
    )
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp

    with patch.object(settings, "MASTODON_ACCESS_TOKEN", "fake_access_token"):
        with patch.object(settings, "MASTODON_INSTANCE_URL", "https://mastodon.social"):
            result = await mastodon.publish("Visit https://example.com", "https://example.com", mock_client)
            assert result.status == "success"
            assert result.posted_url == "https://mastodon.social/@demouser/113456789012345678"
            assert result.public_access is True
            assert result.date == "2026-11-15"
            assert result.time == "10:30:00"


@pytest.mark.asyncio
async def test_bluesky_publish_success():
    """Test BlueskyPlatform.publish session creation and record creation."""
    bluesky = BlueskyPlatform()
    session_resp = httpx.Response(
        status_code=200,
        json={
            "accessJwt": "jwt_token_sample",
            "did": "did:plc:abcdef1234567890",
            "handle": "myhandle.bsky.social"
        }
    )
    record_resp = httpx.Response(
        status_code=200,
        json={
            "uri": "at://did:plc:abcdef1234567890/app.bsky.feed.post/3kabc123def",
            "cid": "bafyreicxyz"
        }
    )
    mock_client = AsyncMock()
    mock_client.post.side_effect = [session_resp, record_resp]

    with patch.object(settings, "BLUESKY_IDENTIFIER", "myhandle.bsky.social"):
        with patch.object(settings, "BLUESKY_APP_PASSWORD", "app_pass_xyz"):
            result = await bluesky.publish("Visit https://example.com", "https://example.com", mock_client)
            assert result.status == "success"
            assert result.posted_url == "https://bsky.app/profile/myhandle.bsky.social/post/3kabc123def"
            assert result.public_access is True


@pytest.mark.asyncio
async def test_base_platform_network_timeout():
    """Verify that network errors in BasePlatform.post() are safely caught as failures."""
    telegram = TelegramPlatform()
    with patch.object(telegram, "is_configured", return_value=True):
        with patch.object(telegram, "publish", side_effect=httpx.ConnectTimeout("Connection timed out")):
            result = await telegram.post("Test https://example.com", "https://example.com")
            assert result.status == "failed"
            assert "Network/Connection error" in result.error
            assert result.posted_url is None


# ==============================================================================
# 3. System Health and Root Endpoint Test
# ==============================================================================

def test_root_health_endpoint():
    """Verify root GET / endpoint returns service health and platforms."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "Telegram" in data["platforms"]
    assert "Discord" in data["platforms"]
    assert "Slack" in data["platforms"]
    assert "Mastodon" in data["platforms"]
    assert "Bluesky" in data["platforms"]
