const api = require("../../utils/api");

const trendNames = ["Agentic Workflow", "端侧多模态", "AI Browser", "RAG 评测", "GPU 供给"];

Page({
  data: {
    trends: []
  },

  onShow() {
    this.loadTrends();
  },

  async loadTrends() {
    const payload = await api.getItems();
    const counts = new Map();
    (payload.items || []).forEach((item) => counts.set(item.category, (counts.get(item.category) || 0) + 1));
    const max = Math.max(...counts.values(), 1);
    const trends = Array.from(counts.entries()).slice(0, 5).map(([category, count], index) => ({
      name: trendNames[index] || category,
      delta: index === 4 ? -6 : 42 - index * 7,
      deltaPrefix: index === 4 ? "" : "+",
      deltaClass: index === 4 ? "negative" : "positive",
      width: Math.max(32, Math.round((count / max) * 86)),
      barClass: index === 4 ? "red" : index === 1 ? "cyan" : index === 3 ? "amber" : "primary"
    }));
    this.setData({ trends });
  }
});
