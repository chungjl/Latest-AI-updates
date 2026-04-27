const api = require("../../utils/api");

Page({
  data: {
    bookmarks: []
  },

  onShow() {
    this.loadBookmarks();
  },

  async loadBookmarks() {
    const bookmarks = await api.getBookmarks();
    this.setData({ bookmarks });
  },

  async removeBookmark(event) {
    await api.deleteBookmark(event.currentTarget.dataset.id);
    await this.loadBookmarks();
    wx.showToast({ title: "已取消", icon: "none" });
  },

  openDetail(event) {
    const item = this.data.bookmarks[event.currentTarget.dataset.index];
    wx.setStorageSync("currentArticle", { ...item, id: item.article_id });
    wx.navigateTo({ url: "/pages/detail/detail" });
  },

  goBack() {
    wx.navigateBack();
  }
});
