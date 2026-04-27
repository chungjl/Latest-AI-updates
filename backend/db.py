from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql:///latest_ai_updates")


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        yield conn


def adapt_json(value: Any) -> Jsonb:
    return Jsonb(value)


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def iso(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    return value


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sources (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  url TEXT NOT NULL,
  type TEXT NOT NULL DEFAULT '媒体/博客',
  kind TEXT NOT NULL DEFAULT 'feed',
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  config JSONB NOT NULL DEFAULT '{}'::jsonb,
  failure_count INTEGER NOT NULL DEFAULT 0,
  last_success_at TIMESTAMPTZ,
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS articles (
  id TEXT PRIMARY KEY,
  source_id BIGINT REFERENCES sources(id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  url TEXT NOT NULL UNIQUE,
  summary TEXT NOT NULL DEFAULT '',
  published_at TIMESTAMPTZ,
  category TEXT NOT NULL DEFAULT '综合资讯',
  importance INTEGER NOT NULL DEFAULT 1,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  raw JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_articles_published ON articles ((COALESCE(published_at, fetched_at)) DESC);
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles (category);
CREATE INDEX IF NOT EXISTS idx_articles_source_id ON articles (source_id);

CREATE TABLE IF NOT EXISTS refresh_runs (
  id BIGSERIAL PRIMARY KEY,
  trigger TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  finished_at TIMESTAMPTZ NOT NULL,
  duration_seconds NUMERIC NOT NULL,
  success BOOLEAN NOT NULL,
  fetched INTEGER NOT NULL,
  stored INTEGER NOT NULL,
  new_items INTEGER NOT NULL,
  errors JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS summaries (
  article_id TEXT PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
  one_liner TEXT NOT NULL,
  why_important TEXT NOT NULL,
  audience TEXT NOT NULL,
  provider TEXT NOT NULL DEFAULT 'local',
  model TEXT NOT NULL DEFAULT 'rule-based',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS daily_briefs (
  brief_date DATE PRIMARY KEY,
  title TEXT NOT NULL,
  highlights JSONB NOT NULL,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT '综合资讯',
  summary TEXT NOT NULL DEFAULT '',
  source_count INTEGER NOT NULL DEFAULT 0,
  article_count INTEGER NOT NULL DEFAULT 0,
  importance INTEGER NOT NULL DEFAULT 1,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS event_articles (
  event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  PRIMARY KEY (event_id, article_id)
);

CREATE INDEX IF NOT EXISTS idx_events_last_seen ON events (last_seen_at DESC);

CREATE TABLE IF NOT EXISTS bookmarks (
  article_id TEXT PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
  note TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS topics (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  keywords TEXT[] NOT NULL DEFAULT '{}',
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(SCHEMA_SQL)
