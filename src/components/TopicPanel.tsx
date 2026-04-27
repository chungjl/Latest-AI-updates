import { Plus, Radar } from "lucide-react";
import type { Topic } from "../types";

type TopicPanelProps = {
  topics: Topic[];
  topicName: string;
  topicKeywords: string;
  saving: boolean;
  onTopicNameChange: (value: string) => void;
  onTopicKeywordsChange: (value: string) => void;
  onCreateTopic: () => void;
};

export function TopicPanel({
  topics,
  topicName,
  topicKeywords,
  saving,
  onTopicNameChange,
  onTopicKeywordsChange,
  onCreateTopic,
}: TopicPanelProps) {
  return (
    <section className="panel topicPanel">
      <div className="panelHeader">
        <div>
          <p>Topic Tracking</p>
          <h3>专题追踪</h3>
        </div>
        <Radar size={18} />
      </div>

      <div className="topicList">
        {topics.map((topic) => (
          <a key={topic.id} className="topicChip" href={`/api/topics/${topic.id}/articles`} target="_blank" rel="noreferrer">
            {topic.name}
            <span>{topic.keywords.length}</span>
          </a>
        ))}
      </div>

      <div className="topicForm">
        <input value={topicName} onChange={(event) => onTopicNameChange(event.target.value)} placeholder="专题名称" />
        <input
          value={topicKeywords}
          onChange={(event) => onTopicKeywordsChange(event.target.value)}
          placeholder="关键词，用逗号分隔"
        />
        <button type="button" onClick={onCreateTopic} disabled={saving || !topicName.trim() || !topicKeywords.trim()}>
          <Plus size={15} />
          新增专题
        </button>
      </div>
    </section>
  );
}
