"""Request-layer interfaces and a safe, injectable Douyin API adapter.

No real private platform endpoints are defined here. The concrete fetch methods
are placeholders until researchers wire in lawful, documented, and accessible
data sources for their own study context.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, MutableMapping, Optional, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import CrawlerConfig
from .cookie import CookieManager
from .models import RawComment
from .rate_limit import RateLimiter, SleepInterval


@dataclass(frozen=True)
class CommentPage:
    """One page of comments returned by an accessible platform endpoint."""

    comments: Sequence[RawComment]
    cursor: Optional[str] = None
    has_more: bool = False
    page_number: int = 1


class CommentAPIClient(Protocol):
    """Protocol implemented by concrete comment API clients."""

    def fetch_top_level_comments(
        self, video_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        """Fetch one page of first-level comments for a video."""

    def fetch_replies(
        self, video_id: str, comment_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        """Fetch one page of replies for a comment, when the endpoint exposes it."""


class TransportResponse(Protocol):
    """Minimal response protocol used by the injectable transport."""

    status_code: int
    text: str

    def json(self) -> Mapping[str, Any]:
        """Return parsed JSON content."""


Transport = Callable[..., TransportResponse]


class DouyinAPIError(RuntimeError):
    """Base exception for the API adapter."""


class DouyinRequestError(DouyinAPIError):
    """Raised when a request fails after all retry attempts."""


class DouyinHTTPError(DouyinAPIError):
    """Raised when a response has a non-success HTTP status."""


class DouyinAPIClient:
    """Safe API adapter with headers, cookie, timeout, retry, and rate limiting."""

    def __init__(
        self,
        config: CrawlerConfig | None = None,
        *,
        cookie_manager: CookieManager | None = None,
        rate_limiter: RateLimiter | None = None,
        transport: Transport | None = None,
    ) -> None:
        """Create a client without binding any real Douyin endpoint URLs."""

        self.config = config or CrawlerConfig()
        self.cookie_manager = cookie_manager or CookieManager(self.config.cookie_file)
        self.rate_limiter = rate_limiter or RateLimiter(
            SleepInterval(self.config.sleep_min_seconds, self.config.sleep_max_seconds)
        )
        self.transport = transport or self._urllib_transport

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        """Execute a JSON request with retry, timeout, cookies, and rate limiting."""

        if not url:
            raise ValueError("url is required")

        request_headers = self._build_headers(headers)
        request_url = self._with_query(url, params)
        attempts = self.config.max_retry + 1
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            self.rate_limiter.wait()
            try:
                response = self.transport(
                    method=method.upper(),
                    url=request_url,
                    headers=request_headers,
                    timeout=self.config.request_timeout,
                )
                if response.status_code < 200 or response.status_code >= 300:
                    raise DouyinHTTPError(
                        f"HTTP {response.status_code} for {method.upper()} {request_url}: "
                        f"{response.text}"
                    )
                return response.json()
            except Exception as exc:
                last_error = exc
                if attempt >= attempts:
                    break

        raise DouyinRequestError(
            f"Request failed after {attempts} attempt(s): {method.upper()} {request_url}: {last_error}"
        ) from last_error

    def fetch_top_level_comments(
        self, video_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        """Placeholder for lawful top-level comment fetching."""

        raise NotImplementedError(
            "No real Douyin comment endpoint is configured in this adapter. "
            "Use a mock client in tests or implement a lawful accessible source."
        )

    def fetch_comment_replies(
        self, video_id: str, comment_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        """Placeholder for lawful reply fetching."""

        raise NotImplementedError(
            "No real Douyin reply endpoint is configured in this adapter. "
            "Use a mock client in tests or implement a lawful accessible source."
        )

    def fetch_replies(
        self, video_id: str, comment_id: str, cursor: Optional[str] = None
    ) -> CommentPage:
        """Collector-compatible alias for fetching replies."""

        return self.fetch_comment_replies(video_id, comment_id, cursor)

    def fetch_video_metadata(self, video_id: str) -> Mapping[str, Any]:
        """Placeholder for lawful video metadata fetching."""

        raise NotImplementedError(
            "No real Douyin metadata endpoint is configured in this adapter. "
            "Use a mock client in tests or implement a lawful accessible source."
        )

    def _build_headers(self, headers: Mapping[str, str] | None = None) -> dict[str, str]:
        """Build request headers from config, local cookie file, and overrides."""

        merged: MutableMapping[str, str] = {
            "User-Agent": self.config.user_agent,
            "Accept": "application/json,text/plain,*/*",
        }
        cookie = self.cookie_manager.load_cookie_header()
        merged["Cookie"] = cookie
        if headers:
            merged.update(headers)
        return dict(merged)

    @staticmethod
    def _with_query(url: str, params: Mapping[str, Any] | None = None) -> str:
        """Attach query parameters to a URL."""

        if not params:
            return url
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}{urlencode(params)}"

    @staticmethod
    def _urllib_transport(
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        timeout: float,
    ) -> TransportResponse:
        """Default stdlib HTTP transport used only when caller invokes request()."""

        request = Request(url, headers=dict(headers), method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                status_code = int(response.status)
                text = response.read().decode("utf-8")
        except HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return _JSONResponse(status_code=exc.code, text=text)
        except URLError as exc:
            raise DouyinRequestError(f"Network request failed: {exc}") from exc
        return _JSONResponse(status_code=status_code, text=text)


@dataclass(frozen=True)
class _JSONResponse:
    """Small response wrapper for stdlib transport."""

    status_code: int
    text: str

    def json(self) -> Mapping[str, Any]:
        """Parse response text as a JSON object."""

        payload = json.loads(self.text)
        if not isinstance(payload, Mapping):
            raise ValueError("response JSON must be an object")
        return payload
