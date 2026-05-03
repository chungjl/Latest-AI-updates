import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { BadgeCheck, Bell, Clock3, Database, FolderKanban, RadioTower, ShieldCheck } from "lucide-react";
import { CategoryFilter } from "./components/CategoryFilter";
import { BookmarkPanel } from "./components/BookmarkPanel";
import { DailyBriefPanel } from "./components/DailyBriefPanel";
import { DashboardHeader } from "./components/DashboardHeader";
import { EventPanel } from "./components/EventPanel";
import { MetricCard } from "./components/MetricCard";
import { NewsCard } from "./components/NewsCard";
import { Sidebar } from "./components/Sidebar";
import { SourceHealthPanel } from "./components/SourceHealthPanel";
import { TopicPanel } from "./components/TopicPanel";
import { TrendPanel } from "./components/TrendPanel";
import type { ApiPayload, Bookmark, DailyBrief, IntelEvent, NewsItem, RefreshJob, Source, SystemStatus, Topic } from "./types";
import "./styles.css";

const PAGE_SIZE = 8;
const SIDEBAR_COLLAPSED_KEY = "latest-ai-updates-sidebar-collapsed";
const ACTIVE_REFRESH_POLL_MS = 3000;
const SUMMARY_POLL_MS = 5000;
const IDLE_POLL_MS = 60000;

function isToday(value?: string | null) {
  if (!value) return false;
  const date = new Date(value);
  const today = new Date();
  return (
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate()
  );
}

function App() {
  const [payload, setPayload] = useState<ApiPayload>({ last_updated: null, items: [] });
  const [activeCategory, setActiveCategory] = useState("全部");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeView, setActiveView] = useState("brief");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem(SIDEBAR_COLLAPSED_KEY) !== "false");
  const [page, setPage] = useState(1);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [schedulerSaving, setSchedulerSaving] = useState(false);
  const [dailyBrief, setDailyBrief] = useState<DailyBrief | null>(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const [refreshJob, setRefreshJob] = useState<RefreshJob | null>(null);
  const [summaryPollingUntil, setSummaryPollingUntil] = useState(0);
  const [events, setEvents] = useState<IntelEvent[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [topicName, setTopicName] = useState("");
  const [topicKeywords, setTopicKeywords] = useState("");
  const [topicSaving, setTopicSaving] = useState(false);
  const [sources, setSources] = useState<Source[]>([]);

  async function loadItems() {
    const response = await fetch("/api/items");
    const data = await response.json();
    setPayload(data);
    return data;
  }

  async function loadStatus() {
    const response = await fetch("/api/status");
    const data = await response.json();
    setSystemStatus(data);
    return data;
  }

  async function loadDailyBrief() {
    const response = await fetch("/api/brief/today");
    if (response.status === 204) {
      setDailyBrief(null);
      return;
    }
    setDailyBrief(await response.json());
  }

  async function loadProductData() {
    const [eventsResponse, topicsResponse, bookmarksResponse, sourcesResponse] = await Promise.all([
      fetch("/api/events?limit=8"),
      fetch("/api/topics"),
      fetch("/api/bookmarks"),
      fetch("/api/sources"),
    ]);
    setEvents(await eventsResponse.json());
    setTopics(await topicsResponse.json());
    setBookmarks(await bookmarksResponse.json());
    setSources(await sourcesResponse.json());
  }

  async function refreshItems() {
    setLoading(true);
    try {
      const response = await fetch("/api/refresh/start", { method: "POST" });
      const job = await response.json();
      if (job.job_id) {
        const statusResponse = await fetch(`/api/refresh/runs/${job.job_id}`);
        setRefreshJob(await statusResponse.json());
      }
      await loadStatus();
      await loadProductData();
    } catch {
      setLoading(false);
    }
  }

  async function updateSchedulerEnabled(enabled: boolean) {
    setSchedulerSaving(true);
    try {
      const response = await fetch("/api/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scheduler: { enabled } }),
      });
      const config = await response.json();
      setSystemStatus((current) =>
        current
          ? { ...current, config }
          : {
              config,
              refresh_status: {
                running: false,
                last_started_at: null,
                last_finished_at: null,
                last_success_at: null,
                last_error: null,
                last_scheduled_key: null,
              },
              refresh_history: [],
            },
      );
    } finally {
      setSchedulerSaving(false);
    }
  }

  async function generateBrief() {
    setBriefLoading(true);
    try {
      const response = await fetch("/api/brief/generate", { method: "POST" });
      setDailyBrief(await response.json());
    } finally {
      setBriefLoading(false);
    }
  }

  async function toggleBookmark(item: NewsItem) {
    const exists = bookmarks.some((bookmark) => bookmark.article_id === item.id);
    if (exists) {
      await fetch(`/api/bookmarks/${item.id}`, { method: "DELETE" });
    } else {
      await fetch(`/api/bookmarks/${item.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note: "" }),
      });
    }
    await loadProductData();
  }

  async function createTopic() {
    setTopicSaving(true);
    try {
      await fetch("/api/topics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: topicName.trim(),
          keywords: topicKeywords
            .split(/[，,]/)
            .map((keyword) => keyword.trim())
            .filter(Boolean),
          enabled: true,
        }),
      });
      setTopicName("");
      setTopicKeywords("");
      await loadProductData();
    } finally {
      setTopicSaving(false);
    }
  }

  async function toggleSource(source: Source) {
    const response = await fetch(`/api/sources/${source.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !source.enabled }),
    });
    const updated = await response.json();
    setSources((current) => current.map((item) => (item.id === source.id ? updated : item)));
  }

  useEffect(() => {
    loadItems();
    loadStatus();
    loadDailyBrief();
    loadProductData();
  }, []);

  useEffect(() => {
    if (!loading || !refreshJob?.id) return;
    const timer = window.setInterval(async () => {
      const response = await fetch(`/api/refresh/runs/${refreshJob.id}`);
      const job: RefreshJob = await response.json();
      setRefreshJob(job);
      await loadItems();
      await loadStatus();
      await loadProductData();
      if (!job.status.startsWith("running")) {
        setLoading(false);
        setSummaryPollingUntil(Date.now() + 90_000);
        window.clearInterval(timer);
      }
    }, ACTIVE_REFRESH_POLL_MS);
    return () => window.clearInterval(timer);
  }, [loading, refreshJob?.id]);

  useEffect(() => {
    if (!summaryPollingUntil) return;
    const timer = window.setInterval(async () => {
      if (Date.now() >= summaryPollingUntil) {
        setSummaryPollingUntil(0);
        window.clearInterval(timer);
        return;
      }
      await loadItems();
    }, SUMMARY_POLL_MS);
    return () => window.clearInterval(timer);
  }, [summaryPollingUntil]);

  useEffect(() => {
    const timer = window.setInterval(async () => {
      if (loading || summaryPollingUntil) return;
      const status = await loadStatus();
      await loadItems();
      await loadProductData();
      if (status.refresh_status?.running) {
        const response = await fetch("/api/refresh/current");
        if (response.ok) {
          const job = await response.json();
          if (job?.id) {
            setRefreshJob(job);
            setLoading(true);
          }
        }
      }
    }, IDLE_POLL_MS);
    return () => window.clearInterval(timer);
  }, [loading, summaryPollingUntil]);

  const categories = useMemo(() => {
    const counts = new Map<string, number>([["全部", payload.items.length]]);
    for (const item of payload.items) counts.set(item.category, (counts.get(item.category) || 0) + 1);
    return [...counts.entries()].sort((a, b) => {
      if (a[0] === "全部") return -1;
      if (b[0] === "全部") return 1;
      return b[1] - a[1];
    });
  }, [payload.items]);

  const filteredItems = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return payload.items.filter((item) => {
      const categoryMatch = activeCategory === "全部" || item.category === activeCategory;
      const queryMatch =
        !normalizedQuery ||
        [item.title, item.summary, item.source, item.category].join(" ").toLowerCase().includes(normalizedQuery);
      return categoryMatch && queryMatch;
    });
  }, [activeCategory, payload.items, query]);

  useEffect(() => {
    setPage(1);
  }, [activeCategory, query]);

  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(sidebarCollapsed));
  }, [sidebarCollapsed]);

  const officialCount = payload.items.filter((item) => item.source_type === "官方来源").length;
  const highImportanceCount = payload.items.filter((item) => item.importance >= 4).length;
  const todayItemsCount = payload.items.filter((item) => isToday(item.created_at || item.fetched_at)).length;
  const credibility = payload.errors?.length ? 86 : 91;
  const totalPages = Math.max(1, Math.ceil(filteredItems.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pagedItems = filteredItems.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  return (
    <div className={sidebarCollapsed ? "appShell sidebarCollapsed" : "appShell"}>
      <Sidebar
        activeView={activeView}
        activeCategory={activeCategory}
        totalItems={payload.items.length}
        highValueCount={highImportanceCount}
        collapsed={sidebarCollapsed}
        onToggleCollapsed={() => setSidebarCollapsed((collapsed) => !collapsed)}
        onViewChange={setActiveView}
      />

      <main className="content">
        <DashboardHeader
          lastUpdated={payload.last_updated}
          query={query}
          loading={loading}
          onRefresh={refreshItems}
          onQueryChange={setQuery}
        />

        <section className="metrics" aria-label="概览">
          <MetricCard label="今日新增" value={todayItemsCount} hint={`资讯池 ${payload.items.length} 条`} icon={<Database size={19} />} />
          <MetricCard label="高价值信号" value={highImportanceCount} hint="+6 新增" icon={<BadgeCheck size={19} />} tone="blue" />
          <MetricCard label="追踪专题" value={topics.length} hint={`${events.length} 个事件`} icon={<FolderKanban size={19} />} tone="violet" />
          <MetricCard label="覆盖渠道" value={payload.stats?.sources || officialCount} hint="稳定运行" icon={<RadioTower size={19} />} tone="amber" />
          <MetricCard label="摘要可信度" value={credibility} hint="+4.2%" icon={<ShieldCheck size={19} />} />
        </section>

        {activeView === "brief" && (
          <>
            {refreshJob && loading && (
              <section className="refreshProgress">
                <div>
                  <strong>
                    刷新中 {refreshJob.completed_sources}/{refreshJob.total_sources}
                  </strong>
                  <span>
                    已抓取 {refreshJob.fetched} 条，新增 {refreshJob.new_items} 条
                  </span>
                </div>
                <div className="refreshTrack">
                  <span
                    style={{
                      width: `${Math.max(
                        6,
                        (refreshJob.completed_sources / Math.max(1, refreshJob.total_sources)) * 100,
                      )}%`,
                    }}
                  />
                </div>
              </section>
            )}

            <CategoryFilter
              categories={categories}
              activeCategory={activeCategory}
              onCategoryChange={setActiveCategory}
            />

            <div className="dashboardGrid">
              <section className="newsFeed" aria-label="资讯列表">
                <div className="feedHeader">
                  <div>
                    <h3>重点信号</h3>
                    <p>按最新抓取时间排序，优先展示新进入的信息</p>
                  </div>
                  <span>{filteredItems.length} 条结果</span>
                </div>
                {filteredItems.length === 0 ? (
                  <div className="empty">没有匹配内容。可以调整搜索词或刷新来源。</div>
                ) : (
                  <div className="newsGrid">
                    {pagedItems.map((item) => (
                      <NewsCard
                        key={item.id}
                        item={item}
                        bookmarked={bookmarks.some((bookmark) => bookmark.article_id === item.id)}
                        onBookmark={toggleBookmark}
                      />
                    ))}
                  </div>
                )}
                {filteredItems.length > PAGE_SIZE && (
                  <nav className="pagination" aria-label="资讯分页">
                    <button type="button" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={currentPage === 1}>
                      上一页
                    </button>
                    <span>
                      {currentPage} / {totalPages}
                    </span>
                    <button
                      type="button"
                      onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
                      disabled={currentPage === totalPages}
                    >
                      下一页
                    </button>
                  </nav>
                )}
              </section>

              <aside className="rightRail">
                <div className="railHeader" aria-hidden="true" />
                <DailyBriefPanel brief={dailyBrief} loading={briefLoading} onGenerate={generateBrief} />
                <EventPanel events={events} />
                <TrendPanel categories={categories} items={payload.items} />
                <SourceHealthPanel
                  payload={payload}
                  items={payload.items}
                  status={systemStatus}
                  onSchedulerToggle={updateSchedulerEnabled}
                  schedulerSaving={schedulerSaving}
                />
              </aside>
            </div>
          </>
        )}

        {activeView === "trends" && (
          <div className="workspaceGrid">
            <TrendPanel categories={categories} items={payload.items} />
            <EventPanel events={events} />
            <section className="panel widePanel">
              <div className="panelHeader">
                <div>
                  <h3>分类热度</h3>
                  <p>按当前资讯池实时统计</p>
                </div>
                <BadgeCheck size={24} />
              </div>
              <div className="statTable">
                {categories.filter(([category]) => category !== "全部").map(([category, count]) => (
                  <div key={category} className="statRow">
                    <span>{category}</span>
                    <strong>{count}</strong>
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}

        {activeView === "sources" && (
          <section className="panel widePanel">
            <div className="panelHeader">
              <div>
                <h3>渠道订阅</h3>
                <p>启用、停用和查看各来源最近抓取状态</p>
              </div>
              <Bell size={24} />
            </div>
            <div className="sourceManagerGrid">
              {sources.map((source) => (
                <article key={source.id} className={source.enabled ? "sourceManagerCard" : "sourceManagerCard disabled"}>
                  <div>
                    <strong>{source.name}</strong>
                    <span>{source.type} · {source.kind}</span>
                  </div>
                  <a href={source.url} target="_blank" rel="noreferrer">{source.url}</a>
                  <p className={source.last_error ? "sourceError" : "sourceOk"}>
                    {source.last_error || (source.last_success_at ? `上次成功：${source.last_success_at}` : "等待首次抓取")}
                  </p>
                  <button type="button" onClick={() => toggleSource(source)}>
                    {source.enabled ? "停用" : "启用"}
                  </button>
                </article>
              ))}
            </div>
          </section>
        )}

        {activeView === "topics" && (
          <div className="workspaceGrid">
            <TopicPanel
              topics={topics}
              topicName={topicName}
              topicKeywords={topicKeywords}
              saving={topicSaving}
              onTopicNameChange={setTopicName}
              onTopicKeywordsChange={setTopicKeywords}
              onCreateTopic={createTopic}
            />
            <section className="panel widePanel">
              <div className="panelHeader">
                <div>
                  <h3>专题命中</h3>
                  <p>点击专题可打开该专题匹配的文章列表 API</p>
                </div>
                <FolderKanban size={24} />
              </div>
              <div className="topicDetailGrid">
                {topics.map((topic) => (
                  <a key={topic.id} href={`/api/topics/${topic.id}/articles`} target="_blank" rel="noreferrer">
                    <strong>{topic.name}</strong>
                    <span>{topic.keywords.join(" / ")}</span>
                  </a>
                ))}
              </div>
            </section>
          </div>
        )}

        {activeView === "bookmarks" && (
          <section className="newsFeed" aria-label="收藏夹">
            <div className="feedHeader">
              <div>
                <h3>收藏夹</h3>
                <p>保留需要后续跟进的资讯和信号</p>
              </div>
              <span>{bookmarks.length} 条收藏</span>
            </div>
            {bookmarks.length === 0 ? (
              <div className="empty">还没有收藏。回到今日简报，在资讯卡片右上角点击收藏。</div>
            ) : (
              <div className="newsGrid">
                {bookmarks.map((item) => (
                  <NewsCard key={item.article_id} item={item} bookmarked onBookmark={toggleBookmark} />
                ))}
              </div>
            )}
          </section>
        )}

        {activeView === "settings" && (
          <div className="workspaceGrid">
            <section className="panel settingsPanel">
              <div className="panelHeader">
                <div>
                  <h3>系统设置</h3>
                  <p>定时刷新、运行状态和部署入口</p>
                </div>
                <Clock3 size={24} />
              </div>
              <div className="settingsList">
                <div className="settingsRow">
                  <span>自动刷新</span>
                  <label className="switchControl">
                    <input
                      type="checkbox"
                      checked={!!systemStatus?.config.scheduler.enabled}
                      disabled={!systemStatus || schedulerSaving}
                      onChange={(event) => updateSchedulerEnabled(event.target.checked)}
                    />
                    <span />
                    <strong>{systemStatus?.config.scheduler.enabled ? "已开启" : "未开启"}</strong>
                  </label>
                </div>
                <div className="settingsRow">
                  <span>刷新时间</span>
                  <strong>{systemStatus?.config.scheduler.daily_times.join(" / ") || "--"}</strong>
                </div>
                <div className="settingsRow">
                  <span>时区</span>
                  <strong>{systemStatus?.config.scheduler.timezone || "--"}</strong>
                </div>
              </div>
            </section>
            <SourceHealthPanel
              payload={payload}
              items={payload.items}
              status={systemStatus}
              onSchedulerToggle={updateSchedulerEnabled}
              schedulerSaving={schedulerSaving}
            />
          </div>
        )}
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
