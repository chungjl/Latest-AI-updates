import { RefreshCw, Search } from "lucide-react";
import { formatDate } from "../utils";

type DashboardHeaderProps = {
  lastUpdated: string | null;
  query: string;
  loading: boolean;
  onRefresh: () => void;
  onQueryChange: (query: string) => void;
};

export function DashboardHeader({ lastUpdated, query, loading, onRefresh, onQueryChange }: DashboardHeaderProps) {
  return (
    <header className="dashboardHeader">
      <div className="headerCopy">
        <p className="headerKicker">AI & TECH INTELLIGENCE</p>
        <h2>每日 AI 技术资讯雷达</h2>
        <p>自动收集多平台、多渠道的 AI 与技术动态，按影响力、可信度和趋势方向进行归因、聚类和摘要。</p>
        <span className="lastUpdated">上次刷新：{lastUpdated ? formatDate(lastUpdated) : "尚未刷新"}</span>
      </div>

      <div className="headerActions">
        <label className="topSearch">
          <Search size={22} />
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="搜索模型、公司、论文、产品..."
          />
        </label>
        <button className="primaryButton" onClick={onRefresh} disabled={loading} aria-label={loading ? "刷新中" : "刷新来源"}>
          <RefreshCw size={18} className={loading ? "spinning" : ""} />
        </button>
      </div>
    </header>
  );
}
