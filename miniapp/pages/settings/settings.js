const api = require("../../utils/api");

Page({
  data: {
    schedulerEnabled: false,
    scheduleText: "--",
    briefText: "尚未生成",
    briefButtonText: "生成",
    briefLoading: false,
    history: []
  },

  onShow() {
    this.loadSettings();
  },

  async loadSettings() {
    const [status, brief] = await Promise.all([
      api.getStatus(),
      api.getTodayBrief().catch(() => null)
    ]);
    const scheduler = status.config.scheduler;
    this.setData({
      schedulerEnabled: !!scheduler.enabled,
      scheduleText: `${scheduler.timezone} · ${scheduler.daily_times.join(" / ")}`,
      history: (status.refresh_history || []).slice(0, 5),
      briefText: brief && brief.generated_at ? `已生成：${brief.generated_at}` : "尚未生成"
    });
  },

  async toggleScheduler(event) {
    const enabled = event.detail.value;
    const config = await api.updateConfig({ scheduler: { enabled } });
    this.setData({
      schedulerEnabled: config.scheduler.enabled,
      scheduleText: `${config.scheduler.timezone} · ${config.scheduler.daily_times.join(" / ")}`
    });
  },

  async generateBrief() {
    this.setData({ briefLoading: true, briefButtonText: "生成中" });
    try {
      const brief = await api.generateBrief();
      this.setData({ briefText: brief.generated_at ? `已生成：${brief.generated_at}` : "已生成" });
      wx.showToast({ title: "已生成", icon: "success" });
    } finally {
      this.setData({ briefLoading: false, briefButtonText: "生成" });
    }
  },

  goBack() {
    wx.navigateBack();
  }
});
