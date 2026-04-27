const api = require("../../utils/api");

function normalizeItem(item) {
  return {
    ...item,
    score: Math.max(70, (item.importance || 1) * 18)
  };
}

const PAGE_SIZE = 10;

Page({
  data: {
    query: "",
    activeCategory: "全部",
    items: [],
    filteredItems: [],
    pagedItems: [],
    categories: [{ name: "全部" }],
    stats: { total: 0, high: 0, credibility: 91 },
    refreshJob: null,
    refreshPercent: 0,
    events: [],
    currentPage: 1,
    totalPages: 1,
    pageText: "1 / 1",
    canPrev: false,
    canNext: false
  },

  onLoad() {
    this.loadItems();
  },

  onShow() {
    this.loadItems();
  },

  async loadItems() {
    try {
      const [payload, events] = await Promise.all([
        api.getItems(),
        api.getEvents(6).catch(() => [])
      ]);
      const items = (payload.items || []).map(normalizeItem);
      const counts = new Map([["全部", items.length]]);
      items.forEach((item) => counts.set(item.category, (counts.get(item.category) || 0) + 1));
      const categories = Array.from(counts.entries()).map(([name, count]) => ({
        name,
        count,
        activeClass: name === this.data.activeCategory ? "active" : ""
      }));
      this.setData({
        items,
        categories,
        events: (events || []).map((event) => ({
          ...event,
          meta: `${event.category} · ${event.article_count} 条 · ${event.source_count} 个来源`
        })),
        stats: {
          total: items.length,
          high: items.filter((item) => item.importance >= 4).length,
          credibility: payload.errors && payload.errors.length ? 86 : 91
        }
      });
      this.applyFilter();
    } catch (error) {
      wx.showToast({ title: "加载失败", icon: "none" });
    }
  },

  applyFilter() {
    const query = this.data.query.trim().toLowerCase();
    const active = this.data.activeCategory;
    const filteredItems = this.data.items
      .filter((item) => active === "全部" || item.category === active)
      .filter((item) => !query || [item.title, item.summary, item.source, item.category].join(" ").toLowerCase().includes(query));
    const totalPages = Math.max(1, Math.ceil(filteredItems.length / PAGE_SIZE));
    const currentPage = Math.min(this.data.currentPage, totalPages);
    const start = (currentPage - 1) * PAGE_SIZE;
    this.setData({
      filteredItems,
      pagedItems: filteredItems.slice(start, start + PAGE_SIZE),
      totalPages,
      currentPage,
      pageText: `${currentPage} / ${totalPages}`,
      canPrev: currentPage > 1,
      canNext: currentPage < totalPages,
      categories: this.data.categories.map((item) => ({
        ...item,
        activeClass: item.name === active ? "active" : ""
      }))
    });
  },

  onSearchInput(event) {
    this.setData({ query: event.detail.value, currentPage: 1 });
    this.applyFilter();
  },

  selectCategory(event) {
    this.setData({ activeCategory: event.currentTarget.dataset.name, currentPage: 1 });
    this.applyFilter();
  },

  openDetail(event) {
    const item = this.data.pagedItems[event.currentTarget.dataset.index];
    wx.setStorageSync("currentArticle", item);
    wx.navigateTo({ url: "/pages/detail/detail" });
  },

  openEvent(event) {
    wx.navigateTo({ url: `/pages/eventDetail/eventDetail?id=${event.currentTarget.dataset.id}` });
  },

  prevPage() {
    if (!this.data.canPrev) return;
    this.setData({ currentPage: this.data.currentPage - 1 });
    this.applyFilter();
  },

  nextPage() {
    if (!this.data.canNext) return;
    this.setData({ currentPage: this.data.currentPage + 1 });
    this.applyFilter();
  },

  async refresh() {
    try {
      const started = await api.startRefresh();
      if (!started.job_id) return;
      this.pollRefresh(started.job_id);
    } catch (error) {
      wx.showToast({ title: "刷新失败", icon: "none" });
    }
  },

  pollRefresh(jobId) {
    if (this.refreshTimer) clearInterval(this.refreshTimer);
    this.refreshTimer = setInterval(async () => {
      const job = await api.getRefreshRun(jobId);
      const refreshPercent = Math.max(6, Math.round((job.completed_sources / Math.max(1, job.total_sources)) * 100));
      this.setData({ refreshJob: job, refreshPercent });
      await this.loadItems();
      if (!job.status.startsWith("running")) {
        clearInterval(this.refreshTimer);
        this.refreshTimer = null;
        setTimeout(() => this.setData({ refreshJob: null }), 1200);
      }
    }, 3000);
  },

  onUnload() {
    if (this.refreshTimer) clearInterval(this.refreshTimer);
  }
});
