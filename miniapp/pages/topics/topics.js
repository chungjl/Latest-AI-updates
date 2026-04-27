const api = require("../../utils/api");

Page({
  data: {
    topics: []
  },

  onShow() {
    this.loadTopics();
  },

  async loadTopics() {
    const topics = await api.getTopics();
    this.setData({
      topics: topics.map((item) => ({
        ...item,
        keywordsText: `${(item.keywords || []).join(" / ") || "暂无关键词"}`
      }))
    });
  },

  openTopic(event) {
    wx.showToast({ title: `专题 ${event.currentTarget.dataset.id}`, icon: "none" });
  },

  openChannels() {
    wx.navigateTo({ url: "/pages/channels/channels" });
  }
});
