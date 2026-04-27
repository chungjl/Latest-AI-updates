const api = require("../../utils/api");

Page({
  data: {
    bookmarkCount: 0,
    sourceCount: 0
  },

  onShow() {
    this.loadProfile();
  },

  async loadProfile() {
    const [bookmarks, sources] = await Promise.all([api.getBookmarks(), api.getSources()]);
    this.setData({ bookmarkCount: bookmarks.length, sourceCount: sources.length });
  },

  openChannels() {
    wx.navigateTo({ url: "/pages/channels/channels" });
  },

  openBookmarks() {
    wx.navigateTo({ url: "/pages/bookmarks/bookmarks" });
  },

  openSettings() {
    wx.navigateTo({ url: "/pages/settings/settings" });
  }
});
