const app = getApp();

function apiBase() {
  return app.globalData.apiBase.replace(/\/$/, "");
}

function request(path, options = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${apiBase()}${path}`,
      method: options.method || "GET",
      data: options.data,
      header: {
        "content-type": "application/json",
        ...(options.header || {})
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
          return;
        }
        reject(new Error(`HTTP ${res.statusCode}`));
      },
      fail: reject
    });
  });
}

module.exports = {
  getItems: () => request("/items"),
  getEvents: () => request("/events?limit=20"),
  getTopics: () => request("/topics"),
  getSources: () => request("/sources"),
  getBookmarks: () => request("/bookmarks"),
  createBookmark: (articleId) => request(`/bookmarks/${articleId}`, { method: "POST", data: { note: "" } }),
  deleteBookmark: (articleId) => request(`/bookmarks/${articleId}`, { method: "DELETE" }),
  startRefresh: () => request("/refresh/start", { method: "POST" }),
  getRefreshRun: (jobId) => request(`/refresh/runs/${jobId}`),
  getTopicArticles: (topicId) => request(`/topics/${topicId}/articles`),
  updateSource: (sourceId, patch) => request(`/sources/${sourceId}`, { method: "PATCH", data: patch })
};
