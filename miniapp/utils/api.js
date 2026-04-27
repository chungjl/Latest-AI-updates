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
  getEvents: (limit = 20) => request(`/events?limit=${limit}`),
  getEventDetail: (eventId) => request(`/events/${eventId}`),
  getTopics: () => request("/topics"),
  createTopic: (topic) => request("/topics", { method: "POST", data: topic }),
  getSources: () => request("/sources"),
  getBookmarks: () => request("/bookmarks"),
  getStatus: () => request("/status"),
  updateConfig: (config) => request("/config", { method: "PUT", data: config }),
  getTodayBrief: () => request("/brief/today"),
  generateBrief: () => request("/brief/generate", { method: "POST" }),
  createBookmark: (articleId) => request(`/bookmarks/${articleId}`, { method: "POST", data: { note: "" } }),
  deleteBookmark: (articleId) => request(`/bookmarks/${articleId}`, { method: "DELETE" }),
  startRefresh: () => request("/refresh/start", { method: "POST" }),
  getRefreshRun: (jobId) => request(`/refresh/runs/${jobId}`),
  getTopicArticles: (topicId) => request(`/topics/${topicId}/articles`),
  updateSource: (sourceId, patch) => request(`/sources/${sourceId}`, { method: "PATCH", data: patch })
};
