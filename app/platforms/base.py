from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Tuple, Optional
import httpx

from app.schemas import PlatformResult
from app.config import settings


class BasePlatform(ABC):
    """
    Abstract Base Class for all social and third-party publishing platforms.
    Each platform handles its own authentication, payload construction,
    API dispatching, and response parsing independently.
    """

    name: str = "BasePlatform"
    public_access: bool = True

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client

    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the required API credentials/configurations for this platform are present.
        """
        pass

    @abstractmethod
    async def publish(self, message: str, cta_url: str, client: httpx.AsyncClient) -> PlatformResult:
        """
        Perform the actual network call to the platform API.
        Must return a PlatformResult object.
        """
        pass

    @abstractmethod
    def simulate_mock_publish(self, message: str, cta_url: str) -> PlatformResult:
        """
        Simulate a successful posting in MOCK_MODE for local testing/demonstration.
        """
        pass

    def get_current_timestamp(self) -> Tuple[str, str]:
        """
        Returns (date_str, time_str) in ISO format (YYYY-MM-DD, HH:MM:SS) in UTC.
        """
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

    def create_success_result(
        self,
        posted_url: str,
        date_str: Optional[str] = None,
        time_str: Optional[str] = None
    ) -> PlatformResult:
        """
        Generate a standardized success PlatformResult.
        """
        default_date, default_time = self.get_current_timestamp()
        return PlatformResult(
            platform=self.name,
            status="success",
            posted_url=posted_url,
            public_access=self.public_access,
            date=date_str or default_date,
            time=time_str or default_time,
            error=None
        )

    def create_failure_result(self, error: str) -> PlatformResult:
        """
        Generate a standardized failed PlatformResult.
        """
        return PlatformResult(
            platform=self.name,
            status="failed",
            posted_url=None,
            public_access=self.public_access,
            date=None,
            time=None,
            error=error
        )

    async def post(self, message: str, cta_url: str) -> PlatformResult:
        """
        Safe execution wrapper that guarantees failure isolation.
        If any exception occurs, it will be safely caught and mapped to a failed PlatformResult
        without breaking execution of other platforms.
        """
        if not self.is_configured():
            if settings.MOCK_MODE:
                return self.simulate_mock_publish(message, cta_url)
            return self.create_failure_result(
                f"Authentication failed: Missing credentials for {self.name}"
            )

        try:
            timeout = httpx.Timeout(settings.REQUEST_TIMEOUT)
            if self._client:
                return await self.publish(message, cta_url, self._client)
            else:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    return await self.publish(message, cta_url, client)
        except httpx.HTTPStatusError as e:
            return self.create_failure_result(
                f"API Error ({e.response.status_code}): {e.response.text[:200]}"
            )
        except httpx.RequestError as e:
            return self.create_failure_result(
                f"Network/Connection error: {str(e)}"
            )
        except Exception as e:
            return self.create_failure_result(
                f"Unexpected error: {str(e)}"
            )
