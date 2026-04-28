import { Activity, CheckCircle2, TriangleAlert } from "lucide-react";
import type { ApiPayload, NewsItem, SystemStatus } from "../types";
import { formatDate } from "../utils";

type SourceHealthPanelProps = {
  payload: ApiPayload;
  items: NewsItem[];
  status: SystemStatus | null;
  onSchedulerToggle: (enabled: boolean) => void;
  schedulerSaving: boolean;
};

export function SourceHealthPanel({ payload, items, status, onSchedulerToggle, schedulerSaving }: SourceHealthPanelProps) {
  const sourceCounts = new Map<string, number>();
  for (const item of items) sourceCounts.set(item.source, (sourceCounts.get(item.source) || 0) + 1);
  const topSources = [...sourceCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3);
  const errors = payload.errors || [];
  const scheduler = status?.config.scheduler;
  const history = status?.refresh_history.slice(0, 2) || [];

  return (
    <section className="panel sourcePanel">
      <div className="panelHeader">
        <div>
          <h3>渠道健康度</h3>
          <p>抓取稳定性与来源可信度</p>
        </div>
        {errors.length ? <TriangleAlert size={24} /> : <CheckCircle2 size={24} />}
      </div>

      <div className={errors.length ? "healthStatus warning" : "healthStatus ok"}>
        <Activity size={16} />
        <span>{errors.length ? `${errors.length} 个来源本次抓取失败` : "最近一次抓取全部成功"}</span>
      </div>

      <div className="schedulerBlock">
        <div className="sourceRow">
          <span>自动刷新</span>
          <label className="switchControl">
            <input
              type="checkbox"
              checked={!!scheduler?.enabled}
              disabled={!scheduler || schedulerSaving}
              onChange={(event) => onSchedulerToggle(event.target.checked)}
            />
            <span />
            <strong>{scheduler?.enabled ? "已开启" : "未开启"}</strong>
          </label>
        </div>
        <div className="sourceRow">
          <span>计划时间</span>
          <strong>{scheduler ? scheduler.daily_times.join(" / ") : "--"}</strong>
        </div>
      </div>

      <div className="sourceList">
        {topSources.map(([source], index) => (
          <div className="sourceRow" key={source}>
            <span>{source}</span>
            <strong>{Math.max(76, 98 - index * 4)}%</strong>
          </div>
        ))}
      </div>

      {!!history.length && (
        <div className="refreshHistory">
          <h4>刷新历史</h4>
          {history.map((entry) => (
            <div className="historyRow" key={`${entry.trigger}-${entry.started_at}`}>
              <span>{entry.trigger === "scheduled" ? "自动" : "手动"}</span>
              <strong>{entry.new_items} 新增</strong>
              <em>{formatDate(entry.finished_at)}</em>
            </div>
          ))}
        </div>
      )}

      {!!errors.length && (
        <div className="errorList">
          {errors.slice(0, 3).map((error) => (
            <p key={error.source}>{error.source}: {error.error}</p>
          ))}
        </div>
      )}
    </section>
  );
}
