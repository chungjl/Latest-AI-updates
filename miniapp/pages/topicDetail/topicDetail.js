const api = require("../../utils/api");

Page({
  data: {
    id: null,
    title: "专题",
    items: []
  },

  onLoad(options) {
    this.setData({ id: options.id });
    this.loadTopic(options.id);
  },

  async loadTopic(id) {
    const [topics, items] = await Promise.all([api.getTopics(), api.getTopicArticles(id)]);
    const topic = topics.find((item) => String(item.id) === String(id));
    this.setData({ title: topic ? topic.name : "专题", items });
  },

  openDetail(event) {
    const item = this.data.items[event.currentTarget.dataset.index];
    wx.setStorageSync("currentArticle", item);
    wx.navigateTo({ url: "/pages/detail/detail" });
  },

  goBack() {
    wx.navigateBack();
  }
});
