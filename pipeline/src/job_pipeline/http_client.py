"""Async HTTP client with per-key concurrency/delay rate limiting and retries."""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any

import httpx

from job_pipeline.config import ATS_RATE_LIMITS, DEFAULT_USER_AGENT


class AsyncRateLimiter:
    """Per-bucket concurrency semaphore and minimum inter-request delay."""

    def __init__(self, limits: dict[str, tuple[int, float]] | None = None):
        self._limits = limits if limits is not None else ATS_RATE_LIMITS
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._last: dict[str, float] = {}

    def _ensure(self, bucket: str) -> tuple[asyncio.Semaphore, asyncio.Lock, float]:
        max_conc, delay = self._limits.get(bucket, (6, 0.1))
        if bucket not in self._semaphores:
            self._semaphores[bucket] = asyncio.Semaphore(max(1, max_conc))
            self._locks[bucket] = asyncio.Lock()
            self._last[bucket] = 0.0
        return self._semaphores[bucket], self._locks[bucket], delay

    @asynccontextmanager
    async def slot(self, bucket: str):
        sem, lock, delay = self._ensure(bucket)
        async with sem:
            if delay > 0:
                async with lock:
                    now = time.monotonic()
                    wait = self._last[bucket] + delay - now
                    if wait > 0:
                        await asyncio.sleep(wait)
                    self._last[bucket] = time.monotonic()
            yield


class HttpClient:
    """Thin async wrapper over httpx.AsyncClient with retries and rate limiting."""

    def __init__(
        self,
        timeout: float = 25.0,
        max_retries: int = 2,
        user_agent: str = DEFAULT_USER_AGENT,
        rate_limiter: AsyncRateLimiter | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limiter = rate_limiter or AsyncRateLimiter()
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            headers={"User-Agent": user_agent, "Accept": "application/json, text/plain, */*"},
            limits=httpx.Limits(max_connections=80, max_keepalive_connections=30),
        )

    async def __aenter__(self) -> "HttpClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def request(
        self,
        method: str,
        url: str,
        *,
        bucket: str = "default",
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with self.rate_limiter.slot(bucket):
                    resp = await self._client.request(
                        method,
                        url,
                        headers=headers,
                        params=params,
                        json=json_body,
                        timeout=timeout or self.timeout,
                    )
                if resp.status_code in (429, 502, 503, 504) and attempt < self.max_retries:
                    retry_after = resp.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after and retry_after.isdigit() else (0.5 * (2**attempt))
                    await asyncio.sleep(min(delay, 5.0))
                    continue
                return resp
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                raise
        assert last_exc is not None
        raise last_exc

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post_json(self, url: str, payload: Any, **kwargs) -> httpx.Response:
        return await self.request("POST", url, json_body=payload, **kwargs)
