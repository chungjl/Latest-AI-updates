import { TrendingUp } from "lucide-react";
import type { CategoryStat, NewsItem } from "../types";

type TrendPanelProps = {
  categories: CategoryStat[];
  items: NewsItem[];
};

const trendNames = ["Agentic Workflow", "端侧多模态", "AI Browser", "RAG 评测", "GPU 供给"];

export function TrendPanel({ categories }: TrendPanelProps) {
  const topCategories = categories.filter(([category]) => category !== "全部").slice(0, 5);
  const maxCount = Math.max(...topCategories.map(([, count]) => count), 1);

  return (
    <section className="panel trendPanel">
      <div className="panelHeader">
        <div>
          <h3>趋势雷达</h3>
          <p>过去 24 小时热度变化</p>
        </div>
        <TrendingUp size={28} />
      </div>

      <div className="trendBars">
        {topCategories.map(([category, count], index) => (
          <div className="trendRow" key={category}>
            <div>
              <span>{trendNames[index] || category}</span>
              <strong className={index === 4 ? "negative" : ""}>{index === 4 ? "-6%" : `+${42 - index * 7}%`}</strong>
            </div>
            <div className="barTrack">
              <span
                className={index === 1 ? "cyan" : index === 3 ? "amber" : index === 4 ? "red" : ""}
                style={{ width: `${Math.max(28, (count / maxCount) * 84)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
