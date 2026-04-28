import type React from "react";
import { ArrowUpRight, Bookmark, BookmarkCheck, Clock3, ShieldCheck } from "lucide-react";
import type { NewsItem } from "../types";
import { formatDate } from "../utils";

type NewsCardProps = {
  item: NewsItem;
  bookmarked?: boolean;
  onBookmark?: (item: NewsItem) => void;
};

export function NewsCard({ item, bookmarked = false, onBookmark }: NewsCardProps) {
  const accent = accentForCategory(item.category);
  const primaryTitle = item.ai_one_liner || item.title;
  const whyImportant = item.ai_why_important;

  return (
    <article className="newsCard" style={{ "--card-accent": accent } as React.CSSProperties}>
      <div className="newsTopline">
        <span className={item.source_type === "官方来源" ? "sourcePill official" : "sourcePill"}>
          {item.source_type === "官方来源" && <ShieldCheck size={13} />}
          {item.source}
        </span>
        <span className="impactPill">影响力 {Math.max(70, item.importance * 18)}</span>
      </div>

      <div className="newsTitleRow">
        <a className="newsTitle" href={item.url} target="_blank" rel="noreferrer">
          {primaryTitle}
          <ArrowUpRight size={20} />
        </a>
        {onBookmark && (
          <button
            type="button"
            className={bookmarked ? "bookmarkButton active" : "bookmarkButton"}
            onClick={() => onBookmark(item)}
            aria-label={bookmarked ? "取消收藏" : "收藏"}
          >
            {bookmarked ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}
          </button>
        )}
      </div>

      <div className="aiDigest">
        <span>原始标题</span>
        <p>{item.title}</p>
        {whyImportant && <small>{whyImportant}</small>}
      </div>

      <footer className="newsFooter">
        <span>{item.category}</span>
        <span>{item.source_type}</span>
        {item.published_at && (
          <span>
            <Clock3 size={14} />
            {formatDate(item.published_at)}
          </span>
        )}
      </footer>
    </article>
  );
}

function accentForCategory(category: string) {
  if (category.includes("多模态")) return "#06B6D4";
  if (category.includes("产品")) return "#10B981";
  if (category.includes("开发")) return "#10B981";
  if (category.includes("研究")) return "#F59E0B";
  if (category.includes("商业")) return "#EF4444";
  return "#6366F1";
}
