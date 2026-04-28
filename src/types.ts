export type NewsItem = {
  id: string;
  title: string;
  url: string;
  summary: string;
  published_at: string | null;
  fetched_at: string;
  source: string;
  source_type: string;
  category: string;
  importance: number;
  ai_one_liner?: string;
  ai_why_important?: string;
  ai_audience?: string;
  ai_provider?: string;
  ai_model?: string;
};

export type ApiPayload = {
  last_updated: string | null;
  items: NewsItem[];
  errors?: { source: string; error: string }[];
  stats?: { sources: number; fetched: number; stored: number };
};

export type CategoryStat = [category: string, count: number];

export type RefreshHistoryEntry = {
  trigger: string;
  started_at: string;
  finished_at: string;
  duration_seconds: number;
  success: boolean;
  fetched: number;
  stored: number;
  new_items: number;
  errors: { source: string; error: string }[];
};

export type SystemStatus = {
  config: {
    scheduler: {
      enabled: boolean;
      timezone: string;
      daily_times: string[];
      run_on_startup: boolean;
    };
  };
  refresh_status: {
    running: boolean;
    last_started_at: string | null;
    last_finished_at: string | null;
    last_success_at: string | null;
    last_error: { source: string; error: string } | null;
    last_scheduled_key: string | null;
  };
  refresh_history: RefreshHistoryEntry[];
};

export type DailyBrief = {
  brief_date: string;
  title: string;
  generated_at?: string;
  highlights: Array<{
    title: string;
    source?: string;
    category?: string;
    one_liner: string;
    why_important: string;
    url: string;
  }>;
};

export type IntelEvent = {
  id: string;
  title: string;
  category: string;
  summary: string;
  source_count: number;
  article_count: number;
  importance: number;
  first_seen_at: string;
  last_seen_at: string;
  updated_at: string;
};

export type Topic = {
  id: number;
  name: string;
  keywords: string[];
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type Bookmark = NewsItem & {
  article_id: string;
  note: string;
  created_at: string;
};

export type Source = {
  id: number;
  name: string;
  url: string;
  type: string;
  kind: string;
  enabled: boolean;
  failure_count: number;
  last_success_at: string | null;
  last_error: string | null;
};

export type RefreshJob = {
  id: string;
  trigger: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  total_sources: number;
  completed_sources: number;
  fetched: number;
  stored: number;
  new_items: number;
  errors: { source: string; error: string }[];
  sources: Array<{
    source_name: string;
    status: string;
    fetched: number;
    error: string | null;
    duration_seconds: number | null;
    updated_at: string;
  }>;
};
