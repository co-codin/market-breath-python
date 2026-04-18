import asyncio
import time
import urllib.parse

import httpx

from .config import (
    BARCHART_HOME,
    BARCHART_QUERY_URL,
    COOKIE_TTL_SECONDS,
    QUERY_DEFAULTS,
    USER_AGENT,
)


class BarchartClient:
    """Async Barchart CSV fetcher that primes an anonymous XSRF session."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None
        self._xsrf: str | None = None
        self._primed_at: float = 0.0

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _ensure_primed(self, *, force: bool = False) -> None:
        async with self._lock:
            fresh = (
                self._client is not None
                and not force
                and (time.monotonic() - self._primed_at) < COOKIE_TTL_SECONDS
            )
            if fresh:
                return
            if self._client is not None:
                await self._client.aclose()
            self._client = httpx.AsyncClient(
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=10.0,
                follow_redirects=True,
            )
            resp = await self._client.get(BARCHART_HOME)
            resp.raise_for_status()
            xsrf = self._client.cookies.get("XSRF-TOKEN")
            self._xsrf = urllib.parse.unquote(xsrf) if xsrf else None
            self._primed_at = time.monotonic()

    async def _do_fetch(self, symbol: str) -> tuple[int, bytes]:
        assert self._client is not None
        params = {"symbol": symbol, **QUERY_DEFAULTS}
        resp = await self._client.get(
            BARCHART_QUERY_URL,
            params=params,
            headers={
                "Accept": "text/csv,*/*;q=0.8",
                "Referer": f"https://www.barchart.com/stocks/quotes/{symbol}",
                "X-XSRF-TOKEN": self._xsrf or "",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        resp.raise_for_status()
        return resp.status_code, resp.content

    async def fetch_csv(self, symbol: str) -> tuple[int, bytes]:
        await self._ensure_primed()
        try:
            return await self._do_fetch(symbol)
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                await self._ensure_primed(force=True)
                return await self._do_fetch(symbol)
            raise
