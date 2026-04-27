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
    this.setData({ sources });
  },

  async toggleSource(event) {
    const index = event.currentTarget.dataset.index;
    const source = this.data.sources[index];
    const updated = await api.updateSource(source.id, { enabled: event.detail.value });
    this.setData({ [`sources[${index}]`]: updated });
  },

  goBack() {
    wx.navigateBack();
  }
});
