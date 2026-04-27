const api = require("../../utils/api");

Page({
  data: {
    topics: [],
    topicName: "",
    topicKeywords: ""
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
    wx.navigateTo({ url: `/pages/topicDetail/topicDetail?id=${event.currentTarget.dataset.id}` });
  },

  onNameInput(event) {
    this.setData({ topicName: event.detail.value });
  },

  onKeywordsInput(event) {
    this.setData({ topicKeywords: event.detail.value });
  },

  async createTopic() {
    const name = this.data.topicName.trim();
    const keywords = this.data.topicKeywords
      .split(/[，,]/)
      .map((item) => item.trim())
      .filter(Boolean);
    if (!name || !keywords.length) {
      wx.showToast({ title: "请填写专题和关键词", icon: "none" });
      return;
    }
    await api.createTopic({ name, keywords, enabled: true });
    this.setData({ topicName: "", topicKeywords: "" });
    await this.loadTopics();
    wx.showToast({ title: "已创建", icon: "success" });
  }
});
