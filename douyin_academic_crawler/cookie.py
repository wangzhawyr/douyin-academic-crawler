"""Cookie loading helpers for manually supplied research credentials."""

from __future__ import annotations

from pathlib import Path


class CookieFileNotFoundError(FileNotFoundError):
    """Raised when the configured local cookie file is missing."""


class CookieManager:
    """Read a manually exported Cookie header from a local text file."""

    def __init__(self, cookie_file: Path | str = "cookie.txt") -> None:
        """Create a cookie reader for a local cookie.txt file."""

        self.cookie_file = Path(cookie_file)

    def load_cookie_header(self) -> str:
        """Return the Cookie header value from disk.

        This method never performs login, captcha handling, account storage, or
        any form of platform restriction bypass. The user must lawfully obtain
        the cookie and place it in the configured file.
        """

        if not self.cookie_file.exists():
            raise CookieFileNotFoundError(
                f"Cookie file not found: {self.cookie_file}. "
                "Create cookie.txt with a legally obtained Cookie header. "
                "Automatic login, captcha bypass, and password storage are not supported."
            )

        cookie = self.cookie_file.read_text(encoding="utf-8").strip()
        if not cookie:
            raise ValueError(f"Cookie file is empty: {self.cookie_file}")
        return cookie
