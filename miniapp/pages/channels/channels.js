const api = require("../../utils/api");

Page({
  data: {
    sources: []
  },

  onLoad() {
    this.loadSources();
  },

  async loadSources() {
    const sources = await api.getSources();
    this.setData({ sources: sources.map(this.normalizeSource) });
  },

  normalizeSource(source) {
    return {
      ...source,
      healthClass: source.last_error ? "source-error" : "source-ok",
      healthText: source.last_error || (source.last_success_at ? `上次成功：${source.last_success_at}` : "等待首次抓取")
    };
  },

  async toggleSource(event) {
    const index = event.currentTarget.dataset.index;
    const source = this.data.sources[index];
    const updated = await api.updateSource(source.id, { enabled: event.detail.value });
    this.setData({ [`sources[${index}]`]: this.normalizeSource(updated) });
  },

  goBack() {
    wx.navigateBack();
  }
});
