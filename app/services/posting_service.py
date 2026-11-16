import asyncio
from typing import List, Optional
import httpx

from app.platforms.base import BasePlatform
from app.platforms.telegram import TelegramPlatform
from app.platforms.discord import DiscordPlatform
from app.platforms.slack import SlackPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.bluesky import BlueskyPlatform
from app.schemas import PostingResponse, PlatformResult


class PostingService:
    """
    Orchestration service for automated multi-platform publishing.
    Dispatches the validated message to all registered platforms concurrently
    and ensures complete failure isolation between platforms.
    """

    def __init__(self, platforms: Optional[List[BasePlatform]] = None):
        if platforms is not None:
            self.platforms = platforms
        else:
            # Default to the 5 independently integrated platforms
            self.platforms = [
                TelegramPlatform(),
                DiscordPlatform(),
                SlackPlatform(),
                MastodonPlatform(),
                BlueskyPlatform(),
            ]

    async def post_to_all(self, message: str, cta_url: str) -> PostingResponse:
        """
        Dispatches message to all platforms simultaneously using asyncio.gather.
        If any single platform encounters an error or timeout, remaining platforms
        continue uninterrupted.
        """
        tasks = [platform.post(message=message, cta_url=cta_url) for platform in self.platforms]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results: List[PlatformResult] = []
        for platform, res in zip(self.platforms, raw_results):
            if isinstance(res, Exception):
                # Uncaught exception fallback
                processed_results.append(
                    PlatformResult(
                        platform=platform.name,
                        status="failed",
                        posted_url=None,
                        public_access=platform.public_access,
                        date=None,
                        time=None,
                        error=f"Internal failure: {str(res)}"
                    )
                )
            else:
                processed_results.append(res)

        # Overall success is True if at least one platform succeeded
        overall_success = any(r.status == "success" for r in processed_results)

        return PostingResponse(
            success=overall_success,
            results=processed_results
        )


posting_service = PostingService()
