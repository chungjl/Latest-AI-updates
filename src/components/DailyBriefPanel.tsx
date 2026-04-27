import { FileText, Sparkles } from "lucide-react";
import type { DailyBrief } from "../types";
import { formatDate } from "../utils";

type DailyBriefPanelProps = {
  brief: DailyBrief | null;
  loading: boolean;
  onGenerate: () => void;
};

export function DailyBriefPanel({ brief, loading, onGenerate }: DailyBriefPanelProps) {
  return (
    <section className="panel briefPanel">
      <div className="panelHeader">
        <div>
          <h3>每日简报</h3>
          <p>{brief?.generated_at ? formatDate(brief.generated_at) : "生成今日高价值摘要"}</p>
        </div>
        <FileText size={26} />
      </div>

      {brief?.highlights?.length ? (
        <div className="briefList">
          {brief.highlights.slice(0, 3).map((item) => (
            <a href={item.url} key={item.url} target="_blank" rel="noreferrer">
              <span>{item.source || item.category || "AI 情报"}</span>
              <strong>{item.one_liner}</strong>
              <p>{item.why_important}</p>
            </a>
          ))}
        </div>
      ) : (
        <p className="briefEmpty">还没有今日简报。生成后会基于最近资讯给出重点结论和影响说明。</p>
      )}

      <button className="briefButton" type="button" onClick={onGenerate} disabled={loading}>
        <Sparkles size={18} />
        {loading ? "生成中" : brief ? "重新生成" : "生成简报"}
      </button>
    </section>
  );
}
