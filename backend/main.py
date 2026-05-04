from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .news import (
    create_bookmark,
    create_topic,
    generate_daily_brief,
    generate_summaries,
    create_or_update_source,
    get_app_config,
    get_bookmarks,
    get_event_detail,
    get_events,
    get_items,
    get_current_refresh_job_status,
    get_refresh_job_status,
    get_sources,
    get_summaries,
    get_system_status,
    get_today_brief,
    get_topic_articles,
    get_topics,
    regenerate_summary,
    rebuild_event_index,
    remove_bookmark,
    search,
    update_source,
    write_app_config,
)
from .scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    if get_app_config()["scheduler"].get("run_on_startup", False):
        await scheduler.run_refresh(trigger="startup")
    yield
    await scheduler.stop()


app = FastAPI(title="AI Daily Intel API", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://192.168.68.129:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_key_auth(request: Request, call_next):
    api_key = os.getenv("AI_INTEL_API_KEY")
    if not api_key or request.method == "OPTIONS" or not request.url.path.startswith("/api"):
        return await call_next(request)
    if request.url.path == "/api/health":
        return await call_next(request)

    provided = request.headers.get("x-api-key") or request.query_params.get("api_key")
    if provided != api_key:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/items")
def items() -> dict:
    return get_items()


@app.get("/api/sources")
def sources() -> list[dict]:
    return get_sources()


@app.post("/api/sources")
def source_create(source: dict) -> dict:
    return create_or_update_source(source)


@app.patch("/api/sources/{source_id}")
def source_update(source_id: int, patch: dict) -> dict | None:
    return update_source(source_id, patch)


@app.get("/api/summaries")
def summaries(limit: int = 20) -> list[dict]:
    return get_summaries(limit)


@app.post("/api/summaries/generate")
async def summaries_generate(limit: int = 20) -> dict:
    return await generate_summaries(limit)


@app.post("/api/articles/{article_id}/summary/regenerate")
async def article_summary_regenerate(article_id: str) -> dict | None:
    return await regenerate_summary(article_id)


@app.get("/api/brief/today")
def today_brief() -> dict | None:
    return get_today_brief()


@app.post("/api/brief/generate")
async def brief_generate() -> dict:
    return await generate_daily_brief()


@app.get("/api/events")
def events(limit: int = 50) -> list[dict]:
    return get_events(limit)


@app.post("/api/events/rebuild")
def events_rebuild(limit: int = 1000) -> dict:
    return rebuild_event_index(limit)


@app.get("/api/events/{event_id}")
def event_detail(event_id: str) -> dict | None:
    return get_event_detail(event_id)


@app.get("/api/search")
def search_items(q: str, limit: int = 50) -> list[dict]:
    return search(q, limit)


@app.get("/api/bookmarks")
def bookmarks(limit: int = 50) -> list[dict]:
    return get_bookmarks(limit)


@app.post("/api/bookmarks/{article_id}")
def bookmark_create(article_id: str, body: dict | None = None) -> dict | None:
    return create_bookmark(article_id, (body or {}).get("note", ""))


@app.delete("/api/bookmarks/{article_id}")
def bookmark_delete(article_id: str) -> dict:
    return remove_bookmark(article_id)


@app.get("/api/topics")
def topics() -> list[dict]:
    return get_topics()


@app.post("/api/topics")
def topic_create(topic: dict) -> dict:
    return create_topic(topic["name"], topic.get("keywords", []), topic.get("enabled", True))


@app.get("/api/topics/{topic_id}/articles")
def topic_items(topic_id: int, limit: int = 50) -> list[dict]:
    return get_topic_articles(topic_id, limit)


@app.get("/api/status")
def status() -> dict:
    return get_system_status()


@app.get("/api/config")
def config() -> dict:
    return get_app_config()


@app.put("/api/config")
def update_config(config: dict) -> dict:
    return write_app_config(config)


@app.post("/api/refresh")
async def refresh() -> dict:
    return await scheduler.run_refresh(trigger="manual")


@app.get("/api/refresh")
async def refresh_get() -> dict:
    return await scheduler.run_refresh(trigger="manual")


@app.post("/api/refresh/start")
async def refresh_start() -> dict:
    return await scheduler.start_refresh_job(trigger="manual")


@app.get("/api/refresh/current")
def refresh_current() -> dict | None:
    return get_current_refresh_job_status()


@app.get("/api/refresh/runs/{job_id}")
def refresh_run(job_id: str) -> dict | None:
    return get_refresh_job_status(job_id)
