#!/usr/bin/env python3
import email.utils
import hashlib
import html
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = ROOT / "public"
DATA_DIR = ROOT / "data"
DATA_FILE = DATA_DIR / "items.json"
SOURCES_FILE = ROOT / "sources.json"

MAX_ITEMS_PER_SOURCE = 25
REQUEST_TIMEOUT_SECONDS = 18
USER_AGENT = "Latest-AI-updates/0.1 (+local personal AI news dashboard)"

AI_KEYWORDS = {
    "大模型": [
        "gpt",
        "chatgpt",
        "claude",
        "gemini",
        "grok",
        "llama",
        "mistral",
        "model",
        "llm",
        "language model",
    ],
    "产品更新": [
        "release",
        "launch",
        "introducing",
        "updates",
        "feature",
        "chatbot",
        "copilot",
        "assistant",
        "workspace",
    ],
    "Agent": [
        "agent",
        "agents",
        "computer use",
        "tool use",
        "workflow",
        "automation",
        "mcp",
    ],
    "多模态": [
        "image",
        "video",
        "audio",
        "voice",
        "speech",
        "vision",
        "multimodal",
        "sora",
        "veo",
    ],
    "开发者": [
        "api",
        "sdk",
        "developer",
        "code",
        "coding",
        "github",
        "cursor",
        "benchmark",
    ],
    "研究论文": [
        "research",
        "paper",
        "arxiv",
        "training",
        "inference",
        "reasoning",
        "alignment",
        "safety",
    ],
    "商业政策": [
        "funding",
        "acquisition",
        "regulation",
        "policy",
        "lawsuit",
        "copyright",
        "enterprise",
        "partnership",
    ],
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def strip_html(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value):
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except (TypeError, ValueError):
        pass
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except ValueError:
        return None


def text_for(node, names):
    for name in names:
        found = node.find(name)
        if found is not None and found.text:
            return found.text.strip()
    return ""


def attr_for(node, names, attr):
    for name in names:
        found = node.find(name)
        if found is not None and found.attrib.get(attr):
            return found.attrib[attr].strip()
    return ""


def node_text(node):
    return "".join(node.itertext()).strip() if node is not None else ""


def fetch_url(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def parse_feed(xml_text, source):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"XML 解析失败: {exc}") from exc

    items = []
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "content": "http://purl.org/rss/1.0/modules/content/",
        "dc": "http://purl.org/dc/elements/1.1/",
    }

    rss_items = root.findall(".//item")
    atom_items = root.findall(".//atom:entry", ns)

    for raw in rss_items[:MAX_ITEMS_PER_SOURCE]:
        title = strip_html(text_for(raw, ["title"]))
        link = text_for(raw, ["link"]) or attr_for(raw, ["guid"], "href")
        summary = strip_html(
            text_for(raw, ["description", "{http://purl.org/rss/1.0/modules/content/}encoded"])
        )
        published = parse_date(
            text_for(raw, ["pubDate", "published", "updated", "{http://purl.org/dc/elements/1.1/}date"])
        )
        item = normalize_item(source, title, link, summary, published)
        if item:
            items.append(item)

    for raw in atom_items[:MAX_ITEMS_PER_SOURCE]:
        title = strip_html(text_for(raw, ["atom:title"]))
        link = ""
        for link_node in raw.findall("atom:link", ns):
            if link_node.attrib.get("rel") in (None, "", "alternate"):
                link = link_node.attrib.get("href", "").strip()
                break
        summary = strip_html(text_for(raw, ["atom:summary", "atom:content"]))
        published = parse_date(text_for(raw, ["atom:published", "atom:updated"]))
        item = normalize_item(source, title, link, summary, published)
        if item:
            items.append(item)

    return items


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        attrs = dict(attrs)
        href = attrs.get("href")
        if href:
            self.current = {"href": href, "text": []}

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            text = strip_html(" ".join(self.current["text"]))
            if text:
                self.links.append({"href": self.current["href"], "text": text})
            self.current = None


def parse_html_page(html_text, source):
    parser = LinkParser()
    parser.feed(html_text)
    patterns = source.get("link_patterns", [])
    items = []
    seen = set()

    for link in parser.links:
        absolute = urllib.parse.urljoin(source["url"], link["href"])
        parsed = urllib.parse.urlparse(absolute)
        normalized_url = urllib.parse.urlunparse(parsed._replace(fragment="", query=""))
        if normalized_url in seen:
            continue
        if patterns and not any(pattern in parsed.path for pattern in patterns):
            continue
        title = cleanup_title(link["text"], source)
        if len(title) < 8 or title.lower() in {"news", "learn more", "read more"}:
            continue
        seen.add(normalized_url)
        item = normalize_item(source, title, normalized_url, "", None)
        if item:
            items.append(item)
        if len(items) >= MAX_ITEMS_PER_SOURCE:
            break
    return items


def cleanup_title(title, source):
    title = re.sub(r"\s+", " ", title).strip()
    for prefix in source.get("title_prefixes_to_remove", []):
        if title.startswith(prefix):
            title = title[len(prefix) :].strip()
    title = re.sub(
        r"\s+(Product|Announcements|Research|Policy|Company|News|Safety|Engineering)\s+"
        r"[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}\b.*$",
        "",
        title,
    )
    title = re.sub(
        r"^(Product|Announcements|Research|Policy|Company|News|Safety|Engineering)\s+"
        r"[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}\s+",
        "",
        title,
    )
    title = re.sub(
        r"^[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}\s+"
        r"(Product|Announcements|Research|Policy|Company|News|Safety|Engineering)\s+",
        "",
        title,
    )
    if source.get("kind") == "html_page":
        for marker in [" Today,", " We’ve", " We've", " We explain", " This ", " Our ", " A new initiative", " In this report"]:
            if marker in title:
                title = title.split(marker, 1)[0].strip()
                break
    if len(title) > 140:
        title = title[:137].rstrip() + "..."
    return title


def normalize_item(source, title, link, summary, published_at):
    if not title or not link:
        return None
    link = urllib.parse.urljoin(source["url"], link)
    summary = summary[:420]
    fingerprint = hashlib.sha256(link.lower().encode("utf-8")).hexdigest()[:16]
    return {
        "id": fingerprint,
        "title": title,
        "url": link,
        "summary": summary,
        "published_at": published_at,
        "source": source["name"],
        "source_type": source.get("type", "媒体/博客"),
        "source_url": source["url"],
        "category": classify(title, summary),
        "importance": score_importance(title, summary, source),
        "fetched_at": now_iso(),
    }


def classify(title, summary):
    text = f"{title} {summary}".lower()
    scores = []
    for category, keywords in AI_KEYWORDS.items():
        count = sum(1 for keyword in keywords if keyword in text)
        if count:
            scores.append((count, category))
    if not scores:
        return "综合资讯"
    scores.sort(reverse=True)
    return scores[0][1]


def score_importance(title, summary, source):
    text = f"{title} {summary}".lower()
    score = 1
    if source.get("type") == "官方来源":
        score += 2
    if any(word in text for word in ["release", "launch", "introducing", "announcing", "new model"]):
        score += 2
    if any(word in text for word in ["chatgpt", "claude", "gemini", "openai", "anthropic"]):
        score += 1
    if any(word in text for word in ["security", "safety", "regulation", "copyright"]):
        score += 1
    return min(score, 5)


def refresh_items():
    sources = load_json(SOURCES_FILE, [])
    existing = load_json(DATA_FILE, {"items": [], "last_updated": None})
    by_id = {item["id"]: item for item in existing.get("items", [])}
    errors = []
    fetched_count = 0

    for source in sources:
        if not source.get("enabled", True):
            continue
        try:
            text = fetch_url(source["url"])
            if source.get("kind", "feed") == "html_page":
                items = parse_html_page(text, source)
            else:
                items = parse_feed(text, source)
            fetched_count += len(items)
            for item in items:
                if item["id"] in by_id:
                    old = by_id[item["id"]]
                    old.update({k: v for k, v in item.items() if v})
                else:
                    by_id[item["id"]] = item
        except (urllib.error.URLError, socket.timeout, ValueError, KeyError) as exc:
            errors.append({"source": source.get("name", source.get("url", "未知来源")), "error": str(exc)})

    items = list(by_id.values())
    items.sort(key=lambda item: item.get("published_at") or item.get("fetched_at") or "", reverse=True)
    payload = {
        "last_updated": now_iso(),
        "items": items[:500],
        "errors": errors,
        "stats": {
            "sources": len([source for source in sources if source.get("enabled", True)]),
            "fetched": fetched_count,
            "stored": min(len(items), 500),
        },
    }
    write_json(DATA_FILE, payload)
    return payload


def response_json(handler, data, status=200):
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def do_GET(self):
        if self.path == "/api/items":
            response_json(self, load_json(DATA_FILE, {"items": [], "last_updated": None, "errors": []}))
            return
        if self.path == "/api/sources":
            response_json(self, load_json(SOURCES_FILE, []))
            return
        if self.path == "/api/refresh":
            started = time.time()
            payload = refresh_items()
            payload["duration_seconds"] = round(time.time() - started, 2)
            response_json(self, payload)
            return
        return super().do_GET()

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))


def main():
    DATA_DIR.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        write_json(DATA_FILE, {"last_updated": None, "items": [], "errors": []})
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    host = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"AI updates dashboard: http://{host}:{port}")
    if host == "0.0.0.0":
        print(f"From Windows host, try: http://192.168.68.129:{port}")
    print("Refresh data from the page, or open /api/refresh directly.")
    server.serve_forever()


if __name__ == "__main__":
    main()
