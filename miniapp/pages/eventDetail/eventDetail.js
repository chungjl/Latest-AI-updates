const api = require("../../utils/api");

Page({
  data: {
    id: "",
    event: null,
    articles: []
  },

  onLoad(options) {
    this.setData({ id: options.id || "" });
    this.loadEvent(options.id);
  },

  async loadEvent(id) {
    if (!id) return;
    try {
      const event = await api.getEventDetail(id);
      this.setData({
        event,
        articles: event && event.articles ? event.articles : []
      });
    } catch (error) {
      wx.showToast({ title: "加载失败", icon: "none" });
    }
  },

  openArticle(event) {
    const item = this.data.articles[event.currentTarget.dataset.index];
    wx.setStorageSync("currentArticle", item);
    wx.navigateTo({ url: "/pages/detail/detail" });
  },

  goBack() {
    wx.navigateBack();
  }
});
