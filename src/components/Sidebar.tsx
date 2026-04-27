import { ArrowRight, BarChart3, Bell, Bookmark, BrainCircuit, ChevronLeft, FileText, LayoutDashboard, Settings, Sparkles } from "lucide-react";

type SidebarProps = {
  activeView: string;
  activeCategory: string;
  totalItems: number;
  highValueCount: number;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onViewChange: (view: string) => void;
};

const navItems = [
  { id: "brief", label: "今日简报", icon: <LayoutDashboard size={20} /> },
  { id: "trends", label: "趋势雷达", icon: <BarChart3 size={20} /> },
  { id: "sources", label: "渠道订阅", icon: <Bell size={20} /> },
  { id: "topics", label: "专题追踪", icon: <FileText size={20} /> },
  { id: "bookmarks", label: "收藏夹", icon: <Bookmark size={20} /> },
  { id: "settings", label: "系统设置", icon: <Settings size={20} /> },
];

export function Sidebar({
  activeView,
  activeCategory,
  totalItems,
  highValueCount,
  collapsed,
  onToggleCollapsed,
  onViewChange,
}: SidebarProps) {
  return (
    <aside className={collapsed ? "sidebar isCollapsed" : "sidebar"}>
      <button
        className="sidebarToggle"
        type="button"
        onClick={onToggleCollapsed}
        aria-label={collapsed ? "展开侧边栏" : "折叠侧边栏"}
      >
        <ChevronLeft size={20} />
      </button>

      <div className="brandBlock">
        <div className="brandIcon">
          <BrainCircuit size={34} />
        </div>
        <div>
          <h1>AI Intel</h1>
          <p>Daily signal desk</p>
        </div>
      </div>

      <nav className="sideNav" aria-label="主导航">
        {navItems.map((item) => (
          <button
            key={item.label}
            className={activeView === item.id ? "sideNavItem isActive" : "sideNavItem"}
            data-tooltip={item.label}
            type="button"
            onClick={() => onViewChange(item.id)}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="sideInsight">
        <Sparkles size={26} />
        <div>
          <strong>智能日报已生成</strong>
          <span>
            今天聚合 {totalItems} 条资讯，模型已识别 {highValueCount} 个高价值信号。
          </span>
          <button type="button">
            <span>查看报告</span>
            <ArrowRight size={18} />
          </button>
        </div>
      </div>

      <div className="sideFoot">当前筛选：{activeCategory}</div>
    </aside>
  );
}
