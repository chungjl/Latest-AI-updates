import { BookmarkCheck } from "lucide-react";
import type { Bookmark } from "../types";

type BookmarkPanelProps = {
  bookmarks: Bookmark[];
};

export function BookmarkPanel({ bookmarks }: BookmarkPanelProps) {
  return (
    <section className="panel bookmarkPanel">
      <div className="panelHeader">
        <div>
          <p>Saved</p>
          <h3>收藏夹</h3>
        </div>
        <BookmarkCheck size={18} />
      </div>

      <div className="bookmarkList">
        {bookmarks.slice(0, 4).map((item) => (
          <a key={item.article_id} href={item.url} target="_blank" rel="noreferrer">
            <strong>{item.title}</strong>
            <small>{item.source}</small>
          </a>
        ))}
        {bookmarks.length === 0 && <div className="miniEmpty">还没有收藏</div>}
      </div>
    </section>
  );
}
