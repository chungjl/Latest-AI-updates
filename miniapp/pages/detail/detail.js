const api = require("../../utils/api");

Page({
  data: {
    item: {},
    score: 70,
    bookmarked: false
  },

  onLoad() {
    const item = wx.getStorageSync("currentArticle") || {};
    this.setData({
      item,
      score: Math.max(70, (item.importance || 1) * 18)
    });
    this.loadBookmarkState(item.id);
  },

  async loadBookmarkState(articleId) {
    if (!articleId) return;
    const bookmarks = await api.getBookmarks();
    this.setData({ bookmarked: bookmarks.some((item) => item.article_id === articleId) });
  },

  goBack() {
    wx.navigateBack();
  },

  async toggleBookmark() {
    const id = this.data.item.id;
    if (!id) return;
    if (this.data.bookmarked) {
      await api.deleteBookmark(id);
      this.setData({ bookmarked: false });
      wx.showToast({ title: "已取消", icon: "none" });
    } else {
      await api.createBookmark(id);
      this.setData({ bookmarked: true });
      wx.showToast({ title: "已收藏", icon: "success" });
    }
  },

  copyLink() {
    wx.setClipboardData({ data: this.data.item.url || "" });
  }
});
