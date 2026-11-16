import re
from typing import List, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator, model_validator


# Regular expression to extract candidate URLs starting with http:// or https://
URL_REGEX = re.compile(
    r'(https?://[^\s<>"\',]+)',
    re.IGNORECASE
)

# Hostname validation regex (RFC 1123 compliant hostname or valid IP or localhost)
DOMAIN_REGEX = re.compile(
    r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$|^localhost$|^(?:\d{1,3}\.){3}\d{1,3}$'
)


class PostingRequest(BaseModel):
    """
    Request payload for automated multi-platform posting.
    Platform selection is intentionally handled internally by the application.
    """
    message: str = Field(
        ...,
        description="The content to be published. Must be <= 200 characters and contain exactly one valid CTA link.",
        examples=["Check out our latest business platform and grow your online visibility. https://example.com"]
    )

    # Internal helper storage for the validated CTA URL
    _extracted_url: Optional[str] = None

    model_config = {
        "extra": "forbid"  # Reject any extra fields like 'platform' to ensure platform selection is handled internally
    }

    @field_validator("message")
    @classmethod
    def validate_message_length_and_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message cannot be empty or only whitespace.")
        
        if len(v) > 200:
            raise ValueError(
                f"Message must not exceed 200 characters. Current length: {len(v)} characters."
            )
        return v.strip()

    @model_validator(mode="after")
    def validate_single_cta_link(self) -> "PostingRequest":
        """
        Validates:
        1. Exactly one CTA link must be included in the message.
        2. The URL must be valid (proper scheme, hostname, structure).
        """
        raw_matches = URL_REGEX.findall(self.message)
        
        # Clean potential trailing punctuation attached to end of sentences (., ;, !)
        cleaned_urls = []
        for match in raw_matches:
            cleaned = re.sub(r'[\.,;!?]+$', '', match)
            if cleaned:
                cleaned_urls.append(cleaned)

        if len(cleaned_urls) == 0:
            raise ValueError(
                "Exactly one CTA link must be included in the message. Found 0 links."
            )
        
        if len(cleaned_urls) > 1:
            raise ValueError(
                f"Exactly one CTA link must be included in the message. Found {len(cleaned_urls)} links: {cleaned_urls}"
            )

        url = cleaned_urls[0]
        parsed = urlparse(url)

        # Validate scheme
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError(
                f"Invalid URL scheme '{parsed.scheme}'. CTA link must use http:// or https://."
            )

        # Validate netloc / hostname
        hostname = parsed.hostname
        if not hostname:
            raise ValueError(
                f"Invalid URL '{url}'. The URL must contain a valid domain or host."
            )

        # Validate domain structure (e.g. example.com, sub.domain.org, localhost)
        if not DOMAIN_REGEX.match(hostname):
            raise ValueError(
                f"Invalid domain '{hostname}' in CTA link '{url}'. Must be a valid hostname or domain."
            )

        self._extracted_url = url
        return self

    @property
    def cta_url(self) -> str:
        """Returns the validated CTA URL."""
        return self._extracted_url or ""


class PlatformResult(BaseModel):
    """
    Standardized result for each individual platform posting attempt.
    """
    platform: str = Field(..., description="Platform name", examples=["Telegram"])
    status: str = Field(..., description="Success or Failed", examples=["success", "failed"])
    posted_url: Optional[str] = Field(None, description="Published content URL", examples=["https://t.me/channel/123"])
    public_access: bool = Field(..., description="Whether content is publicly accessible", examples=[True, False])
    date: Optional[str] = Field(None, description="Posting date in YYYY-MM-DD", examples=["2026-11-15"])
    time: Optional[str] = Field(None, description="Posting time in HH:MM:SS", examples=["10:30:00"])
    error: Optional[str] = Field(None, description="Error details, if applicable", examples=["Authentication failed"])


class PostingResponse(BaseModel):
    """
    Top-level API response containing results from all integrated platforms.
    """
    success: bool = Field(..., description="Overall operation status (true if at least one platform succeeded)")
    results: List[PlatformResult] = Field(..., description="Individual platform posting outcomes")
