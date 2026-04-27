const api = require("../../utils/api");

function normalizeItem(item) {
  return {
    ...item,
    score: Math.max(70, (item.importance || 1) * 18)
  };
}

Page({
  data: {
    query: "",
    activeCategory: "全部",
    items: [],
    filteredItems: [],
    categories: [{ name: "全部" }],
    stats: { total: 0, high: 0, credibility: 91 },
    refreshJob: null,
    refreshPercent: 0
  },

  onLoad() {
    this.loadItems();
  },

  onShow() {
    this.loadItems();
  },

  async loadItems() {
    try {
      const payload = await api.getItems();
      const items = (payload.items || []).map(normalizeItem);
      const counts = new Map([["全部", items.length]]);
      items.forEach((item) => counts.set(item.category, (counts.get(item.category) || 0) + 1));
      const categories = Array.from(counts.entries()).map(([name, count]) => ({ name, count }));
      this.setData({
        items,
        categories,
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
      .filter((item) => !query || [item.title, item.summary, item.source, item.category].join(" ").toLowerCase().includes(query))
      .slice(0, 30);
    this.setData({ filteredItems });
  },

  onSearchInput(event) {
    this.setData({ query: event.detail.value });
    this.applyFilter();
  },

  selectCategory(event) {
    this.setData({ activeCategory: event.currentTarget.dataset.name });
    this.applyFilter();
  },

  openDetail(event) {
    const item = this.data.filteredItems[event.currentTarget.dataset.index];
    wx.setStorageSync("currentArticle", item);
    wx.navigateTo({ url: "/pages/detail/detail" });
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
