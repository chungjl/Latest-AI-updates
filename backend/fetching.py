from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

import httpx


DEFAULT_SOURCE_FETCH_OPTIONS: dict[str, dict[str, Any]] = {
    "Hugging Face Blog": {
        "proxy_fallback": True,
        "proxy_timeout_seconds": 30,
    },
    "Hacker News: AI": {
        "proxy_fallback": True,
        "proxy_sources": ["Hacker News: AI"],
        "proxy_timeout_seconds": 30,
    },
    "Google DeepMind Blog": {
        "timeout_seconds": 15,
    },
    "MIT News AI": {
        "curl_fallback": True,
        "curl_fallback_statuses": [403],
    },
}

DEFAULT_PROXY_URL = os.getenv("AI_INTEL_FETCH_PROXY_URL", "").strip()
DEFAULT_PROXY_SOURCES = {
    name.strip()
    for name in os.getenv("AI_INTEL_FETCH_PROXY_SOURCES", "Hugging Face Blog").split(",")
    if name.strip()
}

RSS_ACCEPT_HEADER = "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.7"


@dataclass(frozen=True)
class FetchAttempt:
    method: str
    success: bool
    status_code: int | None = None
    error: str | None = None


class SourceFetchError(Exception):
    def __init__(self, message: str, attempts: list[FetchAttempt] | None = None):
        super().__init__(message)
        self.attempts = attempts or []


def source_fetch_options(source: dict[str, Any]) -> dict[str, Any]:
    options = dict(DEFAULT_SOURCE_FETCH_OPTIONS.get(source.get("name", ""), {}))
    configured = source.get("fetch_options")
    if isinstance(configured, dict):
        options.update(configured)
    return options


async def fetch_text(client: httpx.AsyncClient, source: dict[str, Any], timeout_seconds: int) -> str:
    options = source_fetch_options(source)
    request_timeout = int(options.get("timeout_seconds") or timeout_seconds)
    attempts: list[FetchAttempt] = []

    try:
        response = await client.get(source["url"], timeout=request_timeout)
        response.raise_for_status()
        return response.text
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        attempts.append(FetchAttempt("httpx", False, status_code=status_code, error=str(exc)))
        if options.get("curl_fallback") and status_code in set(options.get("curl_fallback_statuses", [])):
            return await fetch_text_with_curl(source, timeout_seconds, attempts)
        if should_try_proxy(source, options):
            return await fetch_text_with_proxy(source, timeout_seconds, attempts)
        raise SourceFetchError(str(exc), attempts) from exc
    except Exception as exc:
        attempts.append(FetchAttempt("httpx", False, error=str(exc) or exc.__class__.__name__))
        if should_try_proxy(source, options):
            return await fetch_text_with_proxy(source, timeout_seconds, attempts)
        raise SourceFetchError(str(exc) or exc.__class__.__name__, attempts) from exc


def should_try_proxy(source: dict[str, Any], options: dict[str, Any]) -> bool:
    if not options.get("proxy_fallback"):
        return False
    proxy_url = proxy_url_for_source(source, options)
    return bool(proxy_url)


def proxy_url_for_source(source: dict[str, Any], options: dict[str, Any]) -> str:
    proxy_url = str(options.get("proxy_url") or DEFAULT_PROXY_URL).strip()
    if not proxy_url:
        return ""
    source_name = source.get("name", "")
    proxy_sources = options.get("proxy_sources")
    if isinstance(proxy_sources, list):
        return proxy_url if source_name in proxy_sources else ""
    return proxy_url if source_name in DEFAULT_PROXY_SOURCES else ""


async def fetch_text_with_proxy(
    source: dict[str, Any],
    timeout_seconds: int,
    attempts: list[FetchAttempt],
) -> str:
    options = source_fetch_options(source)
    proxy_url = proxy_url_for_source(source, options)
    timeout = int(options.get("proxy_timeout_seconds") or timeout_seconds)
    try:
        async with httpx.AsyncClient(
            proxy=proxy_url,
            headers={"User-Agent": options.get("user_agent") or source.get("user_agent") or "Latest-AI-updates/0.2"},
            timeout=httpx.Timeout(timeout, connect=min(8, timeout), read=timeout, write=5, pool=5),
            follow_redirects=True,
            trust_env=False,
        ) as client:
            response = await client.get(source["url"])
            response.raise_for_status()
            return response.text
    except Exception as exc:
        attempts.append(FetchAttempt("proxy", False, error=str(exc) or exc.__class__.__name__))
        raise SourceFetchError(format_attempt_errors(attempts), attempts) from exc


async def fetch_text_with_curl(
    source: dict[str, Any],
    timeout_seconds: int,
    attempts: list[FetchAttempt],
) -> str:
    options = source_fetch_options(source)
    user_agent = str(options.get("user_agent") or source.get("user_agent") or "Latest-AI-updates/0.2")
    process = await asyncio.create_subprocess_exec(
        "curl",
        "-fsSL",
        "--max-time",
        str(timeout_seconds),
        "--connect-timeout",
        str(min(8, timeout_seconds)),
        "-A",
        user_agent,
        "-H",
        f"Accept: {RSS_ACCEPT_HEADER}",
        source["url"],
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await process.communicate()
    except asyncio.CancelledError:
        process.kill()
        await process.communicate()
        raise
    if process.returncode == 0:
        return stdout.decode("utf-8", errors="replace")

    error = stderr.decode("utf-8", errors="replace").strip() or f"curl exited {process.returncode}"
    attempts.append(FetchAttempt("curl", False, error=error))
    raise SourceFetchError(format_attempt_errors(attempts), attempts)


def format_attempt_errors(attempts: list[FetchAttempt]) -> str:
    parts = []
    for attempt in attempts:
        status = f" status={attempt.status_code}" if attempt.status_code else ""
        error = f": {attempt.error}" if attempt.error else ""
        parts.append(f"{attempt.method}{status}{error}")
    return " ; ".join(parts)
