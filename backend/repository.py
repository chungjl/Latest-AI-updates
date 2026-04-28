from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from typing import Any

from .db import adapt_json, get_conn, iso, parse_dt


def upsert_setting(key: str, value: dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (%s, %s, now())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
            """,
            (key, adapt_json(value)),
        )


def get_setting(key: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = %s", (key,)).fetchone()
    return row["value"] if row else None


def upsert_sources(sources: list[dict[str, Any]]) -> None:
    with get_conn() as conn:
        for source in sources:
            config = {k: v for k, v in source.items() if k not in {"name", "url", "type", "kind", "enabled"}}
            conn.execute(
                """
                INSERT INTO sources (name, url, type, kind, enabled, config, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (name) DO UPDATE SET
                  url = EXCLUDED.url,
                  type = EXCLUDED.type,
                  kind = EXCLUDED.kind,
                  enabled = EXCLUDED.enabled,
                  config = EXCLUDED.config,
                  updated_at = now()
                """,
                (
                    source["name"],
                    source["url"],
                    source.get("type", "媒体/博客"),
                    source.get("kind", "feed"),
                    source.get("enabled", True),
                    adapt_json(config),
                ),
            )


def list_sources() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, name, url, type, kind, enabled, config, failure_count, last_success_at, last_error
            FROM sources
            ORDER BY id
            """
        ).fetchall()
    sources = []
    for row in rows:
        config = row.pop("config") or {}
        row.update(config)
        row["last_success_at"] = iso(row["last_success_at"])
        sources.append(dict(row))
    return sources


def upsert_source(source: dict[str, Any]) -> dict[str, Any]:
    upsert_sources([source])
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, name, url, type, kind, enabled, config, failure_count, last_success_at, last_error
            FROM sources
            WHERE name = %s
            """,
            (source["name"],),
        ).fetchone()
    config = row.pop("config") or {}
    row.update(config)
    row["last_success_at"] = iso(row["last_success_at"])
    return dict(row)


def patch_source(source_id: int, patch: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {k: patch[k] for k in ["name", "url", "type", "kind", "enabled"] if k in patch}
    config_patch = {k: v for k, v in patch.items() if k not in allowed}
    if not allowed and not config_patch:
        return get_source(source_id)

    assignments = []
    values: list[Any] = []
    for key, value in allowed.items():
        assignments.append(f"{key} = %s")
        values.append(value)
    if config_patch:
        assignments.append("config = config || %s")
        values.append(adapt_json(config_patch))
    assignments.append("updated_at = now()")
    values.append(source_id)

    with get_conn() as conn:
        conn.execute(f"UPDATE sources SET {', '.join(assignments)} WHERE id = %s", values)
    return get_source(source_id)


def get_source(source_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, name, url, type, kind, enabled, config, failure_count, last_success_at, last_error
            FROM sources
            WHERE id = %s
            """,
            (source_id,),
        ).fetchone()
    if not row:
        return None
    config = row.pop("config") or {}
    row.update(config)
    row["last_success_at"] = iso(row["last_success_at"])
    return dict(row)


def update_source_health(name: str, success: bool, error: str | None = None) -> None:
    with get_conn() as conn:
        if success:
            conn.execute(
                """
                UPDATE sources
                SET failure_count = 0, last_success_at = now(), last_error = NULL, updated_at = now()
                WHERE name = %s
                """,
                (name,),
            )
        else:
            conn.execute(
                """
                UPDATE sources
                SET failure_count = failure_count + 1, last_error = %s, updated_at = now()
                WHERE name = %s
                """,
                (error or "未知错误", name),
            )


def upsert_articles(items: list[dict[str, Any]]) -> tuple[int, int]:
    if not items:
        return 0, count_articles()
    new_items = 0
    with get_conn() as conn:
        for item in items:
            source_row = conn.execute("SELECT id FROM sources WHERE name = %s", (item["source"],)).fetchone()
            existed = conn.execute("SELECT 1 FROM articles WHERE id = %s", (item["id"],)).fetchone()
            if not existed:
                new_items += 1
            conn.execute(
                """
                INSERT INTO articles (
                  id, source_id, title, url, summary, published_at, category, importance, fetched_at, raw, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (id) DO UPDATE SET
                  source_id = EXCLUDED.source_id,
                  title = EXCLUDED.title,
                  url = EXCLUDED.url,
                  summary = EXCLUDED.summary,
                  published_at = COALESCE(EXCLUDED.published_at, articles.published_at),
                  category = EXCLUDED.category,
                  importance = EXCLUDED.importance,
                  fetched_at = COALESCE(articles.fetched_at, EXCLUDED.fetched_at),
                  raw = EXCLUDED.raw,
                  updated_at = now()
                """,
                (
                    item["id"],
                    source_row["id"] if source_row else None,
                    item["title"],
                    item["url"],
                    item.get("summary", ""),
                    parse_dt(item.get("published_at")),
                    item.get("category", "综合资讯"),
                    item.get("importance", 1),
                    parse_dt(item.get("fetched_at")),
                    adapt_json(item),
                ),
            )
        stored = conn.execute("SELECT count(*) AS count FROM articles").fetchone()["count"]
    return new_items, stored


def list_articles(limit: int = 500) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
              a.id, a.title, a.url, a.summary, a.published_at, a.category, a.importance, a.fetched_at,
              s.name AS source, s.type AS source_type, s.url AS source_url,
              sm.one_liner AS ai_one_liner, sm.why_important AS ai_why_important,
              sm.audience AS ai_audience, sm.provider AS ai_provider, sm.model AS ai_model
            FROM articles a
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN summaries sm ON sm.article_id = a.id
            ORDER BY a.fetched_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [article_row(row) for row in rows]


def count_articles() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT count(*) AS count FROM articles").fetchone()["count"]


def article_row(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["published_at"] = iso(item["published_at"])
    item["fetched_at"] = iso(item["fetched_at"])
    item["source"] = item.get("source") or "未知来源"
    item["source_type"] = item.get("source_type") or "媒体/博客"
    item["source_url"] = item.get("source_url") or item["url"]
    item["ai_one_liner"] = item.get("ai_one_liner") or ""
    item["ai_why_important"] = item.get("ai_why_important") or ""
    item["ai_audience"] = item.get("ai_audience") or ""
    item["ai_provider"] = item.get("ai_provider") or ""
    item["ai_model"] = item.get("ai_model") or ""
    return item


def insert_refresh_run(entry: dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO refresh_runs (
              trigger, started_at, finished_at, duration_seconds, success, fetched, stored, new_items, errors
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                entry["trigger"],
                parse_dt(entry["started_at"]),
                parse_dt(entry["finished_at"]),
                entry["duration_seconds"],
                entry["success"],
                entry["fetched"],
                entry["stored"],
                entry["new_items"],
                adapt_json(entry.get("errors", [])),
            ),
        )


def list_refresh_runs(limit: int = 20) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT trigger, started_at, finished_at, duration_seconds, success, fetched, stored, new_items, errors
            FROM refresh_runs
            ORDER BY started_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [
        {
            **dict(row),
            "started_at": iso(row["started_at"]),
            "finished_at": iso(row["finished_at"]),
            "duration_seconds": float(row["duration_seconds"]),
        }
        for row in rows
    ]


def create_refresh_job(job_id: str, trigger: str, started_at: str, total_sources: int) -> dict[str, Any]:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO refresh_jobs (
              id, trigger, status, started_at, total_sources, completed_sources, fetched, stored, new_items, errors, updated_at
            )
            VALUES (%s, %s, 'running', %s, %s, 0, 0, 0, 0, '[]'::jsonb, now())
            ON CONFLICT (id) DO UPDATE SET
              status = 'running',
              started_at = EXCLUDED.started_at,
              finished_at = NULL,
              total_sources = EXCLUDED.total_sources,
              completed_sources = 0,
              fetched = 0,
              stored = 0,
              new_items = 0,
              errors = '[]'::jsonb,
              updated_at = now()
            """,
            (job_id, trigger, parse_dt(started_at), total_sources),
        )
    return get_refresh_job(job_id) or {"id": job_id, "status": "running"}


def upsert_refresh_job_source(
    job_id: str,
    source_name: str,
    status: str,
    fetched: int = 0,
    error: str | None = None,
    duration_seconds: float | None = None,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO refresh_job_sources (job_id, source_name, status, fetched, error, duration_seconds, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (job_id, source_name) DO UPDATE SET
              status = EXCLUDED.status,
              fetched = EXCLUDED.fetched,
              error = EXCLUDED.error,
              duration_seconds = EXCLUDED.duration_seconds,
              updated_at = now()
            """,
            (job_id, source_name, status, fetched, error, duration_seconds),
        )


def update_refresh_job_progress(
    job_id: str,
    completed_delta: int = 0,
    fetched_delta: int = 0,
    new_items_delta: int = 0,
    stored: int | None = None,
    error: dict[str, Any] | None = None,
) -> None:
    with get_conn() as conn:
        row = conn.execute("SELECT errors FROM refresh_jobs WHERE id = %s", (job_id,)).fetchone()
        errors = list(row["errors"] or []) if row else []
        if error:
            errors.append(error)
        conn.execute(
            """
            UPDATE refresh_jobs
            SET completed_sources = completed_sources + %s,
                fetched = fetched + %s,
                new_items = new_items + %s,
                stored = COALESCE(%s, stored),
                errors = %s,
                updated_at = now()
            WHERE id = %s
            """,
            (completed_delta, fetched_delta, new_items_delta, stored, adapt_json(errors), job_id),
        )


def finish_refresh_job(job_id: str, status: str, stored: int | None = None) -> dict[str, Any] | None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE refresh_jobs
            SET status = %s,
                finished_at = now(),
                stored = COALESCE(%s, stored),
                updated_at = now()
            WHERE id = %s
            """,
            (status, stored, job_id),
        )
    return get_refresh_job(job_id)


def refresh_job_row(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["started_at"] = iso(item["started_at"])
    item["finished_at"] = iso(item["finished_at"])
    item["updated_at"] = iso(item["updated_at"])
    return item


def get_refresh_job(job_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        job = conn.execute(
            """
            SELECT id, trigger, status, started_at, finished_at, total_sources, completed_sources,
                   fetched, stored, new_items, errors, updated_at
            FROM refresh_jobs
            WHERE id = %s
            """,
            (job_id,),
        ).fetchone()
        if not job:
            return None
        source_rows = conn.execute(
            """
            SELECT source_name, status, fetched, error, duration_seconds, updated_at
            FROM refresh_job_sources
            WHERE job_id = %s
            ORDER BY updated_at DESC, source_name
            """,
            (job_id,),
        ).fetchall()
    sources = []
    for row in source_rows:
        item = dict(row)
        item["duration_seconds"] = float(item["duration_seconds"]) if item["duration_seconds"] is not None else None
        item["updated_at"] = iso(item["updated_at"])
        sources.append(item)
    return {**refresh_job_row(job), "sources": sources}


def get_current_refresh_job() -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id
            FROM refresh_jobs
            ORDER BY started_at DESC
            LIMIT 1
            """
        ).fetchone()
    return get_refresh_job(row["id"]) if row else None


def upsert_summary(article_id: str, one_liner: str, why_important: str, audience: str, provider: str, model: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO summaries (article_id, one_liner, why_important, audience, provider, model, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (article_id) DO UPDATE SET
              one_liner = EXCLUDED.one_liner,
              why_important = EXCLUDED.why_important,
              audience = EXCLUDED.audience,
              provider = EXCLUDED.provider,
              model = EXCLUDED.model,
              updated_at = now()
            """,
            (article_id, one_liner, why_important, audience, provider, model),
        )


def list_articles_without_summaries(limit: int = 20) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
              a.id, a.title, a.url, a.summary, a.published_at, a.category, a.importance, a.fetched_at,
              s.name AS source, s.type AS source_type, s.url AS source_url
            FROM articles a
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN summaries sm ON sm.article_id = a.id
            WHERE sm.article_id IS NULL
            ORDER BY a.fetched_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [article_row(row) for row in rows]


def list_summaries(limit: int = 20) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT sm.*, a.title, a.url, a.category, s.name AS source
            FROM summaries sm
            JOIN articles a ON a.id = sm.article_id
            LEFT JOIN sources s ON s.id = a.source_id
            ORDER BY sm.updated_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [{**dict(row), "created_at": iso(row["created_at"]), "updated_at": iso(row["updated_at"])} for row in rows]


def upsert_daily_brief(brief_date: date, title: str, highlights: list[dict[str, Any]]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO daily_briefs (brief_date, title, highlights, generated_at)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (brief_date) DO UPDATE SET
              title = EXCLUDED.title,
              highlights = EXCLUDED.highlights,
              generated_at = now()
            """,
            (brief_date, title, adapt_json(highlights)),
        )


def get_daily_brief(brief_date: date) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT brief_date, title, highlights, generated_at FROM daily_briefs WHERE brief_date = %s",
            (brief_date,),
        ).fetchone()
    if not row:
        return None
    return {
        "brief_date": row["brief_date"].isoformat(),
        "title": row["title"],
        "highlights": row["highlights"],
        "generated_at": iso(row["generated_at"]),
    }


STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "into",
    "your",
    "openai",
    "anthropic",
    "google",
    "microsoft",
    "announces",
    "introduces",
    "launches",
    "release",
    "update",
}


def event_signature(title: str, category: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", title.lower())
    keywords = [word for word in words if len(word) >= 4 and word not in STOP_WORDS][:8]
    key = f"{category}:{' '.join(sorted(set(keywords[:5])))}"
    if len(key) < len(category) + 6:
        key = f"{category}:{title.lower()[:80]}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def rebuild_events(limit: int = 1000) -> dict[str, int]:
    articles = list_articles(limit)
    groups: dict[str, list[dict[str, Any]]] = {}
    for article in articles:
        signature = event_signature(article["title"], article.get("category", "综合资讯"))
        groups.setdefault(signature, []).append(article)

    with get_conn() as conn:
        conn.execute("DELETE FROM event_articles")
        conn.execute("DELETE FROM events")
        for event_id, grouped_articles in groups.items():
            grouped_articles.sort(
                key=lambda item: item.get("published_at") or item.get("fetched_at") or "",
                reverse=True,
            )
            lead = max(grouped_articles, key=lambda item: item.get("importance", 1))
            sources = {item.get("source") for item in grouped_articles if item.get("source")}
            times = [parse_dt(item.get("published_at")) or parse_dt(item.get("fetched_at")) for item in grouped_articles]
            valid_times = [value for value in times if value is not None]
            conn.execute(
                """
                INSERT INTO events (
                  id, title, category, summary, source_count, article_count, importance,
                  first_seen_at, last_seen_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                """,
                (
                    event_id,
                    lead["title"],
                    lead.get("category", "综合资讯"),
                    lead.get("summary", ""),
                    len(sources),
                    len(grouped_articles),
                    max(item.get("importance", 1) for item in grouped_articles),
                    min(valid_times) if valid_times else None,
                    max(valid_times) if valid_times else None,
                ),
            )
            for article in grouped_articles:
                conn.execute(
                    "INSERT INTO event_articles (event_id, article_id) VALUES (%s, %s)",
                    (event_id, article["id"]),
                )
    return {"events": len(groups), "articles": len(articles)}


def event_row(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    item["first_seen_at"] = iso(item["first_seen_at"])
    item["last_seen_at"] = iso(item["last_seen_at"])
    item["updated_at"] = iso(item["updated_at"])
    return item


def list_events(limit: int = 50) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, title, category, summary, source_count, article_count, importance,
                   first_seen_at, last_seen_at, updated_at
            FROM events
            ORDER BY last_seen_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return [event_row(row) for row in rows]


def get_event(event_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        event = conn.execute(
            """
            SELECT id, title, category, summary, source_count, article_count, importance,
                   first_seen_at, last_seen_at, updated_at
            FROM events
            WHERE id = %s
            """,
            (event_id,),
        ).fetchone()
        if not event:
            return None
        article_rows = conn.execute(
            """
            SELECT
              a.id, a.title, a.url, a.summary, a.published_at, a.category, a.importance, a.fetched_at,
              s.name AS source, s.type AS source_type, s.url AS source_url,
              sm.one_liner AS ai_one_liner, sm.why_important AS ai_why_important,
              sm.audience AS ai_audience, sm.provider AS ai_provider, sm.model AS ai_model
            FROM event_articles ea
            JOIN articles a ON a.id = ea.article_id
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN summaries sm ON sm.article_id = a.id
            WHERE ea.event_id = %s
            ORDER BY a.fetched_at DESC
            """,
            (event_id,),
        ).fetchall()
    return {**event_row(event), "articles": [article_row(row) for row in article_rows]}


def search_articles(query: str, limit: int = 50) -> list[dict[str, Any]]:
    pattern = f"%{query.strip()}%"
    if not query.strip():
        return []
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
              a.id, a.title, a.url, a.summary, a.published_at, a.category, a.importance, a.fetched_at,
              s.name AS source, s.type AS source_type, s.url AS source_url,
              sm.one_liner AS ai_one_liner, sm.why_important AS ai_why_important,
              sm.audience AS ai_audience, sm.provider AS ai_provider, sm.model AS ai_model
            FROM articles a
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN summaries sm ON sm.article_id = a.id
            WHERE a.title ILIKE %s OR a.summary ILIKE %s OR sm.one_liner ILIKE %s
               OR sm.why_important ILIKE %s OR s.name ILIKE %s OR a.category ILIKE %s
            ORDER BY a.fetched_at DESC
            LIMIT %s
            """,
            (pattern, pattern, pattern, pattern, pattern, pattern, limit),
        ).fetchall()
    return [article_row(row) for row in rows]


def set_bookmark(article_id: str, note: str = "") -> dict[str, Any] | None:
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM articles WHERE id = %s", (article_id,)).fetchone()
        if not exists:
            return None
        conn.execute(
            """
            INSERT INTO bookmarks (article_id, note, created_at)
            VALUES (%s, %s, now())
            ON CONFLICT (article_id) DO UPDATE SET note = EXCLUDED.note
            """,
            (article_id, note),
        )
    return get_bookmark(article_id)


def delete_bookmark(article_id: str) -> bool:
    with get_conn() as conn:
        result = conn.execute("DELETE FROM bookmarks WHERE article_id = %s", (article_id,))
    return result.rowcount > 0


def get_bookmark(article_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT b.article_id, b.note, b.created_at,
                   a.title, a.url, a.summary, a.published_at, a.category, a.importance, a.fetched_at,
                   s.name AS source, s.type AS source_type, s.url AS source_url,
                   sm.one_liner AS ai_one_liner, sm.why_important AS ai_why_important,
                   sm.audience AS ai_audience, sm.provider AS ai_provider, sm.model AS ai_model
            FROM bookmarks b
            JOIN articles a ON a.id = b.article_id
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN summaries sm ON sm.article_id = a.id
            WHERE b.article_id = %s
            """,
            (article_id,),
        ).fetchone()
    if not row:
        return None
    item = article_row(row)
    item["article_id"] = row["article_id"]
    item["note"] = row["note"]
    item["created_at"] = iso(row["created_at"])
    return item


def list_bookmarks(limit: int = 50) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT b.article_id, b.note, b.created_at,
                   a.id, a.title, a.url, a.summary, a.published_at, a.category, a.importance, a.fetched_at,
                   s.name AS source, s.type AS source_type, s.url AS source_url,
                   sm.one_liner AS ai_one_liner, sm.why_important AS ai_why_important,
                   sm.audience AS ai_audience, sm.provider AS ai_provider, sm.model AS ai_model
            FROM bookmarks b
            JOIN articles a ON a.id = b.article_id
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN summaries sm ON sm.article_id = a.id
            ORDER BY b.created_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    items = []
    for row in rows:
        item = article_row(row)
        item["article_id"] = row["article_id"]
        item["note"] = row["note"]
        item["created_at"] = iso(row["created_at"])
        items.append(item)
    return items


def upsert_topic(name: str, keywords: list[str], enabled: bool = True) -> dict[str, Any]:
    clean_keywords = [keyword.strip() for keyword in keywords if keyword.strip()]
    with get_conn() as conn:
        row = conn.execute(
            """
            INSERT INTO topics (name, keywords, enabled, updated_at)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (name) DO UPDATE SET
              keywords = EXCLUDED.keywords,
              enabled = EXCLUDED.enabled,
              updated_at = now()
            RETURNING id, name, keywords, enabled, created_at, updated_at
            """,
            (name.strip(), clean_keywords, enabled),
        ).fetchone()
    return {
        **dict(row),
        "created_at": iso(row["created_at"]),
        "updated_at": iso(row["updated_at"]),
    }


def list_topics() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, keywords, enabled, created_at, updated_at FROM topics ORDER BY id"
        ).fetchall()
    return [
        {
            **dict(row),
            "created_at": iso(row["created_at"]),
            "updated_at": iso(row["updated_at"]),
        }
        for row in rows
    ]


def topic_articles(topic_id: int, limit: int = 50) -> list[dict[str, Any]]:
    with get_conn() as conn:
        topic = conn.execute("SELECT keywords FROM topics WHERE id = %s AND enabled = true", (topic_id,)).fetchone()
        if not topic:
            return []
        keywords = [keyword for keyword in topic["keywords"] if keyword]
        if not keywords:
            return []
        clauses = []
        values: list[Any] = []
        for keyword in keywords:
            pattern = f"%{keyword}%"
            clauses.append("(a.title ILIKE %s OR a.summary ILIKE %s OR sm.one_liner ILIKE %s OR sm.why_important ILIKE %s OR a.category ILIKE %s)")
            values.extend([pattern, pattern, pattern, pattern, pattern])
        values.append(limit)
        rows = conn.execute(
            f"""
            SELECT
              a.id, a.title, a.url, a.summary, a.published_at, a.category, a.importance, a.fetched_at,
              s.name AS source, s.type AS source_type, s.url AS source_url,
              sm.one_liner AS ai_one_liner, sm.why_important AS ai_why_important,
              sm.audience AS ai_audience, sm.provider AS ai_provider, sm.model AS ai_model
            FROM articles a
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN summaries sm ON sm.article_id = a.id
            WHERE {' OR '.join(clauses)}
            ORDER BY a.fetched_at DESC
            LIMIT %s
            """,
            values,
        ).fetchall()
    return [article_row(row) for row in rows]
