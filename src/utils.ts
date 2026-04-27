import type { NewsItem } from "./types";

export function formatDate(value?: string | null) {
  if (!value) return "未知时间";
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function isRecent(value?: string | null) {
  if (!value) return false;
  return Date.now() - new Date(value).getTime() <= 24 * 60 * 60 * 1000;
}

export function getItemTime(item: NewsItem) {
  return item.published_at || item.fetched_at;
}

export function shortNumber(value: number) {
  return new Intl.NumberFormat("zh-CN").format(value);
}
