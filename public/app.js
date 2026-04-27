const state = {
  items: [],
  errors: [],
  category: "全部",
  query: "",
};

const els = {
  updated: document.querySelector("#updated"),
  refresh: document.querySelector("#refresh"),
  search: document.querySelector("#search"),
  tabs: document.querySelector("#tabs"),
  items: document.querySelector("#items"),
  errors: document.querySelector("#errors"),
  total: document.querySelector("#total"),
  official: document.querySelector("#official"),
  today: document.querySelector("#today"),
};

function formatTime(value) {
  if (!value) return "未知时间";
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function isRecent(value) {
  if (!value) return false;
  return Date.now() - new Date(value).getTime() <= 24 * 60 * 60 * 1000;
}

function scoreLabel(score) {
  return "重要度 " + "●".repeat(score || 1);
}

function categories(items) {
  const counts = new Map([["全部", items.length]]);
  for (const item of items) {
    counts.set(item.category, (counts.get(item.category) || 0) + 1);
  }
  return [...counts.entries()].sort((a, b) => {
    if (a[0] === "全部") return -1;
    if (b[0] === "全部") return 1;
    return b[1] - a[1];
  });
}

function filteredItems() {
  const query = state.query.trim().toLowerCase();
  return state.items.filter((item) => {
    const categoryMatch = state.category === "全部" || item.category === state.category;
    const queryMatch =
      !query ||
      [item.title, item.summary, item.source, item.category].join(" ").toLowerCase().includes(query);
    return categoryMatch && queryMatch;
  });
}

function renderStats() {
  els.total.textContent = state.items.length;
  els.official.textContent = state.items.filter((item) => item.source_type === "官方来源").length;
  els.today.textContent = state.items.filter((item) => isRecent(item.published_at || item.fetched_at)).length;
}

function renderTabs() {
  els.tabs.innerHTML = "";
  for (const [category, count] of categories(state.items)) {
    const button = document.createElement("button");
    button.className = "tab" + (category === state.category ? " active" : "");
    button.textContent = `${category} ${count}`;
    button.addEventListener("click", () => {
      state.category = category;
      render();
    });
    els.tabs.append(button);
  }
}

function renderErrors() {
  if (!state.errors.length) {
    els.errors.hidden = true;
    els.errors.innerHTML = "";
    return;
  }
  els.errors.hidden = false;
  els.errors.innerHTML = state.errors
    .map((error) => `<div>${escapeHtml(error.source)}：${escapeHtml(error.error)}</div>`)
    .join("");
}

function renderItems() {
  const items = filteredItems();
  if (!items.length) {
    els.items.innerHTML = `<div class="empty">没有匹配的内容。可以点“刷新来源”先抓取最新条目。</div>`;
    return;
  }

  els.items.innerHTML = items
    .map((item) => {
      const published = item.published_at || item.fetched_at;
      const sourceClass = item.source_type === "官方来源" ? " chip official" : "chip";
      return `
        <article class="item">
          <div class="chips">
            <span class="${sourceClass}">${escapeHtml(item.source_type)}</span>
            <span class="chip">${escapeHtml(item.category)}</span>
            <span class="chip">${escapeHtml(scoreLabel(item.importance))}</span>
          </div>
          <h2><a href="${escapeAttr(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(item.title)}</a></h2>
          <p class="summary-text">${escapeHtml(item.summary || "暂无摘要，点击标题查看原文。")}</p>
          <div class="meta">
            <span>${escapeHtml(item.source)}</span>
            <span>${escapeHtml(formatTime(published))}</span>
          </div>
        </article>
      `;
    })
    .join("");
}

function render() {
  renderStats();
  renderTabs();
  renderErrors();
  renderItems();
}

async function loadItems() {
  const response = await fetch("/api/items");
  const data = await response.json();
  state.items = data.items || [];
  state.errors = data.errors || [];
  els.updated.textContent = data.last_updated
    ? `上次刷新：${formatTime(data.last_updated)}`
    : "还没有抓取数据";
  render();
}

async function refreshItems() {
  els.refresh.disabled = true;
  els.refresh.textContent = "刷新中";
  try {
    const response = await fetch("/api/refresh");
    const data = await response.json();
    state.items = data.items || [];
    state.errors = data.errors || [];
    els.updated.textContent = `上次刷新：${formatTime(data.last_updated)}，抓取 ${data.stats?.fetched || 0} 条`;
    render();
  } finally {
    els.refresh.disabled = false;
    els.refresh.textContent = "刷新来源";
  }
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("`", "&#096;");
}

els.refresh.addEventListener("click", refreshItems);
els.search.addEventListener("input", (event) => {
  state.query = event.target.value;
  renderItems();
});

loadItems();
