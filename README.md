# AI 每日情报

一个本地运行的 AI 资讯看板。后端使用 FastAPI，前端使用 Vite + React + TypeScript。它会从 `sources.json` 里的 RSS/Atom/官方页面来源抓取条目，按关键词分类、去重、保留来源链接，并在 Web 页面里展示。

## 运行

安装后端依赖：

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

安装前端依赖：

```bash
npm install
```

启动后端：

```bash
. .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

启动前端：

```bash
npm run dev
```

虚拟机内打开：

```text
http://127.0.0.1:5173
```

如果在虚拟机里运行、从宿主机 Windows 访问：

```text
http://192.168.68.129:5173
```

第一次打开后点击“刷新来源”。也可以直接访问：

```text
http://127.0.0.1:8000/api/refresh
```

## 数据位置

- 默认来源种子：`sources.json`
- PostgreSQL 数据库：默认 `latest_ai_updates`
- 旧版抓取结果兼容文件：`data/items.json`
- 后端入口：`backend/main.py`
- 前端入口：`src/main.tsx`

## 添加来源

初始化阶段会从 `sources.json` 导入来源。产品运行后可以用 API 添加来源：

```json
{
  "name": "Example AI Blog",
  "url": "https://example.com/feed.xml",
  "type": "官方来源",
  "enabled": true
}
```

`type` 可以用：

- `官方来源`
- `媒体/博客`
- `研究/高校`
- `研究/论文`
- `社区`

## 当前能力

- RSS/Atom/官方 HTML 页面自动抓取
- 每天定时自动刷新，默认北京时间 08:00 和 20:00
- 刷新状态和刷新历史 API
- PostgreSQL 存储来源、文章、刷新记录、摘要和日报
- 事件聚合，把同一主题的多来源报道合并成事件
- 搜索、收藏、专题追踪 API
- 可选 API Key 保护
- Docker Compose 部署模板
- 来源新增/更新/禁用 API
- 本地规则摘要和每日简报生成
- 按链接去重
- 中文分类标签
- 重要度粗评分
- 来源类型和原文链接
- 搜索和分类筛选

## 定时刷新

默认配置在 `app_config.json`：

```json
{
  "scheduler": {
    "enabled": true,
    "timezone": "Asia/Shanghai",
    "daily_times": ["08:00", "20:00"],
    "run_on_startup": false
  }
}
```

状态接口：

```text
GET /api/status
```

## 初始化 PostgreSQL

本地开发默认使用当前系统用户连接数据库：

```bash
sudo -u postgres createuser zhong
sudo -u postgres createdb latest_ai_updates -O zhong
. .venv/bin/activate
PYTHONPATH=. python scripts/setup_db.py
```

如果云服务器上用自定义连接串，设置：

```bash
export DATABASE_URL="postgresql://user:password@127.0.0.1:5432/latest_ai_updates"
```

## 摘要和日报

生成未摘要文章：

```text
POST /api/summaries/generate
```

生成今日简报：

```text
POST /api/brief/generate
```

## 事件、搜索、收藏、专题

重建事件索引：

```text
POST /api/events/rebuild
```

查看事件列表和详情：

```text
GET /api/events
GET /api/events/{event_id}
```

搜索文章：

```text
GET /api/search?q=Claude
```

收藏文章：

```text
POST /api/bookmarks/{article_id}
GET /api/bookmarks
DELETE /api/bookmarks/{article_id}
```

创建专题追踪：

```json
{
  "name": "Agent",
  "keywords": ["agent", "workflow", "mcp"],
  "enabled": true
}
```

```text
POST /api/topics
GET /api/topics
GET /api/topics/{topic_id}/articles
```

## 可选鉴权

默认本地开发不启用鉴权。云服务器上如果只开放 API 给可信客户端，可以设置：

```bash
export AI_INTEL_API_KEY="your-secret"
```

启用后，除 `/api/health` 外的 API 需要传：

```text
x-api-key: your-secret
```

如果前端直接暴露给公网，建议先通过 Nginx、VPN 或登录态保护页面，不要把长期 API Key 写进浏览器代码。

## Docker Compose 部署

```bash
docker compose up -d --build
docker compose exec api python scripts/setup_db.py
```

默认端口：

- Web：`http://服务器IP/`
- API：`http://服务器IP:8000/api/health`

## 下一步建议

1. 把搜索、收藏、专题追踪接入前端页面。
2. 事件聚合升级为 embedding/LLM 聚类，减少同义标题误分组。
3. 增加登录、多用户、权限和审计日志。
4. 增加来源质量评分、失败告警和后台管理页。
