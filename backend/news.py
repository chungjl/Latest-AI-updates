from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.parse
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup

from .db import init_db
from .repository import (
    create_refresh_job,
    delete_bookmark,
    finish_refresh_job,
    get_current_refresh_job,
    get_daily_brief,
    get_event,
    get_refresh_job,
    get_setting,
    insert_refresh_run,
    list_articles,
    list_articles_without_summaries,
    list_bookmarks,
    list_events,
    list_refresh_runs,
    list_sources,
    list_summaries,
    list_topics,
    patch_source,
    rebuild_events,
    search_articles,
    set_bookmark,
    topic_articles,
    update_source_health,
    update_refresh_job_progress,
    upsert_articles,
    upsert_daily_brief,
    upsert_setting,
    upsert_refresh_job_source,
    upsert_source,
    upsert_sources,
    upsert_summary,
    upsert_topic,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_FILE = DATA_DIR / "items.json"
SOURCES_FILE = ROOT / "sources.json"
APP_CONFIG_FILE = ROOT / "app_config.json"
REFRESH_HISTORY_FILE = DATA_DIR / "refresh_history.json"
REFRESH_STATUS_FILE = DATA_DIR / "refresh_status.json"

MAX_ITEMS_PER_SOURCE = 25
REQUEST_TIMEOUT_SECONDS = max(3, int(os.getenv("AI_INTEL_REQUEST_TIMEOUT_SECONDS", "8")))
BACKGROUND_REQUEST_TIMEOUT_SECONDS = max(8, int(os.getenv("AI_INTEL_BACKGROUND_REQUEST_TIMEOUT_SECONDS", "45")))
BACKGROUND_REFRESH_TIMEOUT_SECONDS = max(
    BACKGROUND_REQUEST_TIMEOUT_SECONDS + 10,
    int(os.getenv("AI_INTEL_BACKGROUND_REFRESH_TIMEOUT_SECONDS", str(BACKGROUND_REQUEST_TIMEOUT_SECONDS + 90))),
)
FETCH_CONCURRENCY = max(1, int(os.getenv("AI_INTEL_FETCH_CONCURRENCY", "4")))
SKIP_FAILED_SOURCES_THRESHOLD = max(0, int(os.getenv("AI_INTEL_SKIP_FAILED_SOURCES_THRESHOLD", "0")))
USER_AGENT = "Latest-AI-updates/0.2 (+FastAPI React AI news dashboard)"
logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)
LLM_API_KEY = os.getenv("AI_INTEL_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
LLM_BASE_URL = os.getenv("AI_INTEL_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
LLM_MODEL = os.getenv("AI_INTEL_LLM_MODEL", "gpt-4o-mini")
LLM_MAX_TOKENS = max(256, int(os.getenv("AI_INTEL_LLM_MAX_TOKENS", "1024")))

DEFAULT_APP_CONFIG = {
    "scheduler": {
        "enabled": True,
        "timezone": "Asia/Shanghai",
        "daily_times": ["08:00", "20:00"],
        "run_on_startup": False,
    }
}

AI_KEYWORDS = {
    "大模型": ["gpt", "chatgpt", "claude", "gemini", "grok", "llama", "mistral", "model", "llm"],
    "产品更新": ["release", "launch", "introducing", "updates", "feature", "copilot", "assistant"],
    "Agent": ["agent", "agents", "computer use", "tool use", "workflow", "automation", "mcp"],
    "多模态": ["image", "video", "audio", "voice", "speech", "vision", "multimodal", "sora", "veo"],
    "开发者": ["api", "sdk", "developer", "code", "coding", "github", "cursor", "benchmark"],
    "研究论文": ["research", "paper", "arxiv", "training", "inference", "reasoning", "alignment", "safety"],
    "商业政策": ["funding", "acquisition", "regulation", "policy", "lawsuit", "copyright", "enterprise"],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def get_app_config() -> dict[str, Any]:
    config = get_setting("app_config") or load_json(APP_CONFIG_FILE, DEFAULT_APP_CONFIG)
    scheduler = {**DEFAULT_APP_CONFIG["scheduler"], **config.get("scheduler", {})}
    return {**DEFAULT_APP_CONFIG, **config, "scheduler": scheduler}


def write_app_config(config: dict[str, Any]) -> dict[str, Any]:
    current = get_app_config()
    scheduler = {**current["scheduler"], **config.get("scheduler", {})}
    next_config = {**current, **config, "scheduler": scheduler}
    write_json(APP_CONFIG_FILE, next_config)
    upsert_setting("app_config", next_config)
    return next_config


def get_refresh_history(limit: int = 20) -> list[dict[str, Any]]:
    history = list_refresh_runs(limit)
    if history:
        return history
    return load_json(REFRESH_HISTORY_FILE, [])[:limit]


def get_refresh_status() -> dict[str, Any]:
    return load_json(
        REFRESH_STATUS_FILE,
        {
            "running": False,
            "last_started_at": None,
            "last_finished_at": None,
            "last_success_at": None,
            "last_error": None,
            "last_scheduled_key": None,
        },
    )


def write_refresh_status(status: dict[str, Any]) -> dict[str, Any]:
    next_status = {**get_refresh_status(), **status}
    write_json(REFRESH_STATUS_FILE, next_status)
    return next_status


def record_refresh_history(entry: dict[str, Any]) -> None:
    history = load_json(REFRESH_HISTORY_FILE, [])
    history.insert(0, entry)
    write_json(REFRESH_HISTORY_FILE, history[:100])
    insert_refresh_run(entry)


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = BeautifulSoup(value, "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", text).strip()


def parse_entry_date(entry: Any) -> str | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc).replace(microsecond=0).isoformat()


def classify(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    scores: list[tuple[int, str]] = []
    for category, keywords in AI_KEYWORDS.items():
        count = sum(1 for keyword in keywords if keyword in text)
        if count:
            scores.append((count, category))
    if not scores:
        return "综合资讯"
    scores.sort(reverse=True)
    return scores[0][1]


def score_importance(title: str, summary: str, source: dict[str, Any]) -> int:
    text = f"{title} {summary}".lower()
    score = 1
    if source.get("type") == "官方来源":
        score += 2
    if any(word in text for word in ["release", "launch", "introducing", "announcing", "new model"]):
        score += 2
    if any(word in text for word in ["chatgpt", "claude", "gemini", "openai", "anthropic"]):
        score += 1
    if any(word in text for word in ["security", "safety", "regulation", "copyright"]):
        score += 1
    return min(score, 5)


def normalize_item(
    source: dict[str, Any],
    title: str,
    link: str,
    summary: str = "",
    published_at: str | None = None,
) -> dict[str, Any] | None:
    title = cleanup_title(strip_html(title), source)
    if not title or not link:
        return None
    url = urllib.parse.urljoin(source["url"], link)
    item_id = hashlib.sha256(url.lower().encode("utf-8")).hexdigest()[:16]
    return {
        "id": item_id,
        "title": title,
        "url": url,
        "summary": strip_html(summary)[:420],
        "published_at": published_at,
        "source": source["name"],
        "source_type": source.get("type", "媒体/博客"),
        "source_url": source["url"],
        "category": classify(title, summary),
        "importance": score_importance(title, summary, source),
        "fetched_at": utc_now(),
    }


def cleanup_title(title: str, source: dict[str, Any]) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    title = re.sub(
        r"^(Product|Announcements|Research|Policy|Company|News|Safety|Engineering)\s+"
        r"[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}\s+",
        "",
        title,
    )
    title = re.sub(
        r"^[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}\s+"
        r"(Product|Announcements|Research|Policy|Company|News|Safety|Engineering)\s+",
        "",
        title,
    )
    title = re.sub(
        r"\s+(Product|Announcements|Research|Policy|Company|News|Safety|Engineering)\s+"
        r"[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}\b.*$",
        "",
        title,
    )
    if source.get("kind") == "html_page":
        for marker in [" Today,", " We’ve", " We've", " We explain", " This ", " Our ", " A new initiative"]:
            if marker in title:
                title = title.split(marker, 1)[0].strip()
                break
    if len(title) > 140:
        title = title[:137].rstrip() + "..."
    return title


def parse_feed(text: str, source: dict[str, Any]) -> list[dict[str, Any]]:
    parsed = feedparser.parse(text)
    items = []
    for entry in parsed.entries[:MAX_ITEMS_PER_SOURCE]:
        item = normalize_item(
            source,
            entry.get("title", ""),
            entry.get("link", ""),
            entry.get("summary", "") or entry.get("description", ""),
            parse_entry_date(entry),
        )
        if item:
            items.append(item)
    return items


def parse_html_page(text: str, source: dict[str, Any]) -> list[dict[str, Any]]:
    soup = BeautifulSoup(text, "html.parser")
    patterns = source.get("link_patterns", [])
    seen: set[str] = set()
    items = []
    for anchor in soup.find_all("a", href=True):
        url = urllib.parse.urljoin(source["url"], anchor["href"])
        parsed = urllib.parse.urlparse(url)
        normalized_url = urllib.parse.urlunparse(parsed._replace(query="", fragment=""))
        if normalized_url in seen:
            continue
        if patterns and not any(pattern in parsed.path for pattern in patterns):
            continue
        title = anchor.get_text(" ", strip=True)
        if len(title) < 8 or title.lower() in {"news", "learn more", "read more"}:
            continue
        item = normalize_item(source, title, normalized_url)
        if item:
            seen.add(normalized_url)
            items.append(item)
        if len(items) >= MAX_ITEMS_PER_SOURCE:
            break
    return items


async def fetch_text(client: httpx.AsyncClient, url: str) -> str:
    response = await client.get(url)
    response.raise_for_status()
    return response.text


async def fetch_source_items(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    source: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    async with semaphore:
        started = time.perf_counter()
        source_name = source.get("name", source.get("url", "未知来源"))
        try:
            text = await asyncio.wait_for(fetch_text(client, source["url"]), timeout=timeout_seconds)
            items = parse_html_page(text, source) if source.get("kind") == "html_page" else parse_feed(text, source)
            duration_seconds = round(time.perf_counter() - started, 2)
            logger.info("Fetched source %s in %.2fs with %s items", source_name, duration_seconds, len(items))
            return {
                "source": source_name,
                "success": True,
                "items": items,
                "error": None,
                "duration_seconds": duration_seconds,
            }
        except asyncio.TimeoutError:
            duration_seconds = round(time.perf_counter() - started, 2)
            error_message = f"Timeout after {timeout_seconds}s"
            logger.warning("Failed source %s in %.2fs: %s", source_name, duration_seconds, error_message)
            return {
                "source": source_name,
                "success": False,
                "items": [],
                "error": error_message,
                "duration_seconds": duration_seconds,
            }
        except Exception as exc:
            duration_seconds = round(time.perf_counter() - started, 2)
            error_message = str(exc) or exc.__class__.__name__
            logger.warning("Failed source %s in %.2fs: %s", source_name, duration_seconds, error_message)
            return {
                "source": source_name,
                "success": False,
                "items": [],
                "error": error_message,
                "duration_seconds": duration_seconds,
            }


async def refresh_items(trigger: str = "manual") -> dict[str, Any]:
    ensure_bootstrap()
    started = time.perf_counter()
    started_at = utc_now()
    write_refresh_status({"running": True, "last_started_at": started_at, "last_error": None})
    sources = list_sources()
    errors = []
    fetched_count = 0
    fetched_items: list[dict[str, Any]] = []
    enabled_sources = [source for source in sources if source.get("enabled", True)]
    skipped_sources = [
        source
        for source in enabled_sources
        if SKIP_FAILED_SOURCES_THRESHOLD and source.get("failure_count", 0) >= SKIP_FAILED_SOURCES_THRESHOLD
    ]
    fetch_sources = [source for source in enabled_sources if source not in skipped_sources]
    semaphore = asyncio.Semaphore(FETCH_CONCURRENCY)

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(
            REQUEST_TIMEOUT_SECONDS,
            connect=min(3, REQUEST_TIMEOUT_SECONDS),
            read=REQUEST_TIMEOUT_SECONDS,
            write=3,
            pool=2,
        ),
        limits=httpx.Limits(max_connections=FETCH_CONCURRENCY + 2, max_keepalive_connections=FETCH_CONCURRENCY),
        follow_redirects=True,
        trust_env=False,
    ) as client:
        results = await asyncio.gather(
            *(fetch_source_items(client, semaphore, source, REQUEST_TIMEOUT_SECONDS) for source in fetch_sources),
        )

    for source in skipped_sources:
        logger.info(
            "Skipped source %s after %s consecutive failures",
            source.get("name", source.get("url", "未知来源")),
            source.get("failure_count", 0),
        )

    for result in results:
        if result["success"]:
            items = result["items"]
            fetched_count += len(items)
            fetched_items.extend(items)
            update_source_health(result["source"], True)
        else:
            errors.append({"source": result["source"], "error": result["error"]})
            update_source_health(result["source"], False, result["error"])

    new_items, stored = upsert_articles(fetched_items)
    items = list_articles()
    payload = {
        "last_updated": utc_now(),
        "items": items[:500],
        "errors": errors,
        "stats": {
            "sources": len(enabled_sources),
            "skipped_sources": len(skipped_sources),
            "fetched": fetched_count,
            "stored": stored,
        },
    }
    write_json(DATA_FILE, payload)
    finished_at = utc_now()
    duration_seconds = round(time.perf_counter() - started, 2)
    history_entry = {
        "trigger": trigger,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": duration_seconds,
        "success": not errors,
        "errors": errors,
        "fetched": fetched_count,
        "stored": payload["stats"]["stored"],
        "new_items": new_items,
    }
    record_refresh_history(history_entry)
    rebuild_events()
    asyncio.create_task(enrich_summaries_background(50))
    write_refresh_status(
        {
            "running": False,
            "last_finished_at": finished_at,
            "last_success_at": finished_at if not errors else get_refresh_status().get("last_success_at"),
            "last_error": errors[0] if errors else None,
        }
    )
    payload["refresh"] = history_entry
    return payload


async def refresh_items_job(job_id: str, trigger: str = "manual") -> dict[str, Any]:
    ensure_bootstrap()
    started = time.perf_counter()
    started_at = utc_now()
    write_refresh_status({"running": True, "last_started_at": started_at, "last_error": None})
    sources = list_sources()
    enabled_sources = [source for source in sources if source.get("enabled", True)]
    create_refresh_job(job_id, trigger, started_at, len(enabled_sources))

    errors: list[dict[str, Any]] = []
    fetched_count = 0
    new_items_count = 0
    stored = 0
    semaphore = asyncio.Semaphore(FETCH_CONCURRENCY)

    try:
        async with asyncio.timeout(BACKGROUND_REFRESH_TIMEOUT_SECONDS):
            async with httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT},
                timeout=httpx.Timeout(
                    BACKGROUND_REQUEST_TIMEOUT_SECONDS,
                    connect=min(5, BACKGROUND_REQUEST_TIMEOUT_SECONDS),
                    read=BACKGROUND_REQUEST_TIMEOUT_SECONDS,
                    write=5,
                    pool=5,
                ),
                limits=httpx.Limits(max_connections=FETCH_CONCURRENCY + 2, max_keepalive_connections=FETCH_CONCURRENCY),
                follow_redirects=True,
                trust_env=False,
            ) as client:
                tasks = [
                    asyncio.create_task(fetch_source_items(client, semaphore, source, BACKGROUND_REQUEST_TIMEOUT_SECONDS))
                    for source in enabled_sources
                ]
                for task in asyncio.as_completed(tasks):
                    result = await task
                    if result["success"]:
                        items = result["items"]
                        new_items, stored = upsert_articles(items)
                        fetched_count += len(items)
                        new_items_count += new_items
                        update_source_health(result["source"], True)
                        upsert_refresh_job_source(
                            job_id,
                            result["source"],
                            "success",
                            len(items),
                            None,
                            result.get("duration_seconds"),
                        )
                        update_refresh_job_progress(job_id, 1, len(items), new_items, stored)
                    else:
                        error = {"source": result["source"], "error": result["error"]}
                        errors.append(error)
                        update_source_health(result["source"], False, result["error"])
                        upsert_refresh_job_source(
                            job_id,
                            result["source"],
                            "failed",
                            0,
                            result["error"],
                            result.get("duration_seconds"),
                        )
                        update_refresh_job_progress(job_id, 1, 0, 0, stored or None, error)

                    items = list_articles()
                    write_json(
                        DATA_FILE,
                        {
                            "last_updated": utc_now(),
                            "items": items[:500],
                            "errors": errors,
                            "stats": {
                                "sources": len(enabled_sources),
                                "fetched": fetched_count,
                                "stored": len(items),
                            },
                        },
                    )
    except TimeoutError:
        error = {"source": "refresh-job", "error": f"刷新超过 {BACKGROUND_REFRESH_TIMEOUT_SECONDS}s，已自动停止"}
        errors.append(error)
        write_refresh_status({"running": False, "last_error": error})
        finish_refresh_job(job_id, "failed", stored or len(list_articles()))
        logger.warning("Refresh job %s timed out after %ss", job_id, BACKGROUND_REFRESH_TIMEOUT_SECONDS)
        return get_refresh_job(job_id) or {"id": job_id, "status": "failed", "errors": errors}
    except Exception as exc:
        error = {"source": "refresh-job", "error": type(exc).__name__}
        errors.append(error)
        write_refresh_status({"running": False, "last_error": error})
        finish_refresh_job(job_id, "failed", stored or len(list_articles()))
        logger.exception("Refresh job %s failed", job_id)
        return get_refresh_job(job_id) or {"id": job_id, "status": "failed", "errors": errors}

    items = list_articles()
    stored = len(items)
    finished_at = utc_now()
    duration_seconds = round(time.perf_counter() - started, 2)
    history_entry = {
        "trigger": trigger,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": duration_seconds,
        "success": not errors,
        "errors": errors,
        "fetched": fetched_count,
        "stored": stored,
        "new_items": new_items_count,
    }
    record_refresh_history(history_entry)
    rebuild_events()
    write_refresh_status(
        {
            "running": False,
            "last_finished_at": finished_at,
            "last_success_at": finished_at if not errors else get_refresh_status().get("last_success_at"),
            "last_error": errors[0] if errors else None,
        }
    )
    result = finish_refresh_job(job_id, "completed" if not errors else "completed_with_errors", stored) or history_entry
    asyncio.create_task(enrich_summaries_background(50))
    return result


def get_refresh_job_status(job_id: str) -> dict[str, Any] | None:
    ensure_bootstrap()
    return get_refresh_job(job_id)


def get_current_refresh_job_status() -> dict[str, Any] | None:
    ensure_bootstrap()
    return get_current_refresh_job()


def get_items() -> dict[str, Any]:
    ensure_bootstrap()
    fallback = load_json(DATA_FILE, {"last_updated": None, "items": [], "errors": [], "stats": {}})
    items = list_articles()
    return {**fallback, "items": items, "stats": {**fallback.get("stats", {}), "stored": len(items)}}


def get_sources() -> list[dict[str, Any]]:
    ensure_bootstrap()
    return list_sources()


def create_or_update_source(source: dict[str, Any]) -> dict[str, Any]:
    ensure_bootstrap()
    return upsert_source(source)


def update_source(source_id: int, patch: dict[str, Any]) -> dict[str, Any] | None:
    ensure_bootstrap()
    return patch_source(source_id, patch)


def get_system_status() -> dict[str, Any]:
    ensure_bootstrap()
    return {
        "config": get_app_config(),
        "refresh_status": get_refresh_status(),
        "refresh_history": get_refresh_history(),
    }


def rebuild_event_index(limit: int = 1000) -> dict[str, int]:
    ensure_bootstrap()
    return rebuild_events(limit)


def get_events(limit: int = 50) -> list[dict[str, Any]]:
    ensure_bootstrap()
    events = list_events(limit)
    if not events:
        rebuild_events()
        events = list_events(limit)
    return events


def get_event_detail(event_id: str) -> dict[str, Any] | None:
    ensure_bootstrap()
    return get_event(event_id)


def search(query: str, limit: int = 50) -> list[dict[str, Any]]:
    ensure_bootstrap()
    return search_articles(query, limit)


def create_bookmark(article_id: str, note: str = "") -> dict[str, Any] | None:
    ensure_bootstrap()
    return set_bookmark(article_id, note)


def remove_bookmark(article_id: str) -> dict[str, bool]:
    ensure_bootstrap()
    return {"deleted": delete_bookmark(article_id)}


def get_bookmarks(limit: int = 50) -> list[dict[str, Any]]:
    ensure_bootstrap()
    return list_bookmarks(limit)


def create_topic(name: str, keywords: list[str], enabled: bool = True) -> dict[str, Any]:
    ensure_bootstrap()
    return upsert_topic(name, keywords, enabled)


def get_topics() -> list[dict[str, Any]]:
    ensure_bootstrap()
    return list_topics()


def get_topic_articles(topic_id: int, limit: int = 50) -> list[dict[str, Any]]:
    ensure_bootstrap()
    return topic_articles(topic_id, limit)


def ensure_bootstrap() -> None:
    init_db()
    if not list_sources():
        upsert_sources(load_json(SOURCES_FILE, []))
    if not get_setting("app_config"):
        upsert_setting("app_config", load_json(APP_CONFIG_FILE, DEFAULT_APP_CONFIG))


def is_mostly_chinese(text: str) -> bool:
    if not text:
        return False
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    return chinese_chars >= max(4, len(text) * 0.18)


def compact_text(text: str, limit: int = 160) -> str:
    value = re.sub(r"\s+", " ", text or "").strip()
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def generate_local_summary(item: dict[str, Any]) -> dict[str, str]:
    subject = item["title"].strip()
    summary = item.get("summary") or subject
    category = item.get("category", "综合资讯")
    source = item.get("source", "可信来源")
    if is_mostly_chinese(subject):
        one_liner = compact_text(subject, 90)
    else:
        one_liner = f"{category}方向有新动态：{compact_text(subject, 76)}"
    context = compact_text(summary, 180)
    why = f"这条消息来自{source}，可作为判断{category}趋势的参考。重点关注它是否会影响你使用的产品、开发工具、模型能力或后续采购选择。"
    if item.get("importance", 1) >= 4:
        why = f"这是高优先级信号。{why}"
    audience = "AI 产品、研发、运营和关注行业变化的决策者"
    if "开发" in item.get("category", ""):
        audience = "开发者、技术负责人和工具链使用者"
    if "研究" in item.get("category", ""):
        audience = "研究人员、算法工程师和技术策略负责人"
    return {
        "one_liner": one_liner,
        "why_important": why,
        "audience": audience,
        "context": context,
    }


async def generate_llm_summary(item: dict[str, Any]) -> dict[str, str] | None:
    if not LLM_API_KEY:
        return None
    prompt = {
        "title": item.get("title", ""),
        "source": item.get("source", ""),
        "category": item.get("category", ""),
        "summary": item.get("summary", ""),
        "url": item.get("url", ""),
    }
    messages = [
        {
            "role": "system",
            "content": "你是面向中文个人用户的 AI 资讯编辑。请把英文或中文资讯提炼成容易理解的中文，不要夸大，不要编造。",
        },
        {
            "role": "user",
            "content": (
                "基于下面资讯，输出 JSON，字段为 one_liner、why_important、audience。"
                "one_liner 用一句中文说明发生了什么；why_important 用 1-2 句说明对普通 AI 使用者或开发者的影响；"
                "audience 说明适合谁关注。\n\n"
                f"{json.dumps(prompt, ensure_ascii=False)}"
            ),
        },
    ]
    try:
        async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
            response = await client.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": LLM_MODEL,
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": LLM_MAX_TOKENS,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        if not data.get("one_liner") or not data.get("why_important"):
            return None
        return {
            "one_liner": compact_text(str(data["one_liner"]), 140),
            "why_important": compact_text(str(data["why_important"]), 260),
            "audience": compact_text(str(data.get("audience") or "关注 AI 产品和技术变化的用户"), 120),
        }
    except Exception as exc:
        logger.warning("LLM summary failed for %s: %s", item.get("id"), exc)
        return None


async def generate_summaries(limit: int = 20) -> dict[str, Any]:
    ensure_bootstrap()
    items = list_articles_without_summaries(limit)
    for item in items:
        llm_summary = await generate_llm_summary(item)
        summary = llm_summary or generate_local_summary(item)
        upsert_summary(
            item["id"],
            summary["one_liner"],
            summary["why_important"],
            summary["audience"],
            "llm" if llm_summary else "local",
            LLM_MODEL if llm_summary else "rule-based",
        )
    return {"generated": len(items), "items": list_summaries(limit)}


async def enrich_summaries_background(limit: int = 50) -> None:
    try:
        await generate_summaries(limit)
    except Exception:
        logger.exception("Background summary enrichment failed")


def get_summaries(limit: int = 20) -> list[dict[str, Any]]:
    ensure_bootstrap()
    return list_summaries(limit)


async def generate_daily_brief() -> dict[str, Any]:
    ensure_bootstrap()
    today = datetime.now(timezone.utc).date()
    summaries = list_summaries(10)
    if len(summaries) < 5:
        await generate_summaries(20)
        summaries = list_summaries(10)
    highlights = [
        {
            "title": item["title"],
            "source": item.get("source"),
            "category": item.get("category"),
            "one_liner": item["one_liner"],
            "why_important": item["why_important"],
            "url": item["url"],
        }
        for item in summaries[:10]
    ]
    title = f"{today.isoformat()} AI 每日简报"
    upsert_daily_brief(today, title, highlights)
    return get_daily_brief(today) or {"brief_date": today.isoformat(), "title": title, "highlights": highlights}


def get_today_brief() -> dict[str, Any] | None:
    ensure_bootstrap()
    return get_daily_brief(datetime.now(timezone.utc).date())
