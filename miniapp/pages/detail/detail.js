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
      item: {
        ...item,
        readableSummary: item.ai_one_liner || item.summary || "暂无中文解读，建议复制原文链接后在浏览器查看。",
        readableWhy: item.ai_why_important || "这条资讯已保留原文链接，建议结合来源可信度和发布时间判断是否需要继续跟踪。",
        readableAudience: item.ai_audience || "关注 AI 产品和技术变化的用户"
      },
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
  },

  shareText() {
    const item = this.data.item;
    wx.setClipboardData({ data: `${item.title}\n${item.readableSummary || item.summary || ""}\n${item.url || ""}` });
  }
});
