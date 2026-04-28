import { GitMerge, Layers3 } from "lucide-react";
import type { IntelEvent } from "../types";

type EventPanelProps = {
  events: IntelEvent[];
};

export function EventPanel({ events }: EventPanelProps) {
  return (
    <section className="panel eventPanel">
      <div className="panelHeader">
        <div>
          <p>Event Clusters</p>
          <h3>事件聚合</h3>
        </div>
        <GitMerge size={18} />
      </div>

      <div className="eventList">
        {events.slice(0, 3).map((event) => (
          <a key={event.id} className="eventItem" href={`/api/events/${event.id}`} target="_blank" rel="noreferrer">
            <span className="eventIcon">
              <Layers3 size={15} />
            </span>
            <span>
              <strong>{event.title}</strong>
              <small>
                {event.category} · {event.article_count} 条 · {event.source_count} 个来源
              </small>
            </span>
          </a>
        ))}
        {events.length === 0 && <div className="miniEmpty">暂无事件聚合</div>}
      </div>
    </section>
  );
}
