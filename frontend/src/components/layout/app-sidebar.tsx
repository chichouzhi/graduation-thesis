import { BookOpenText, Files, LayoutDashboard, MessagesSquare, SquareKanban } from "lucide-react";
import { NavLink } from "react-router-dom";

import { cn } from "@/lib/utils";

const items = [
  { to: "/app/dashboard", label: "工作台", icon: LayoutDashboard },
  { to: "/app/chat", label: "AI 对话", icon: MessagesSquare },
  { to: "/app/documents", label: "文档分析", icon: Files },
  { to: "/app/topics", label: "选题中心", icon: BookOpenText },
  { to: "/app/taskboard", label: "任务看板", icon: SquareKanban },
];

export function AppSidebar() {
  return (
    <aside className="app-sidebar">
      <div>
        <p className="brand-kicker">Graduation Topic Support</p>
        <h1 className="brand-title">毕业设计选题支持系统</h1>
        <p className="brand-text">智能推荐与流程管理演示平台。</p>
      </div>

      <nav className="nav-list">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => cn("nav-link", isActive && "active")}
          >
            <item.icon size={18} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <small>Student Workspace</small>
        <strong>当前聚焦：智能选题与文献分析推进中</strong>
      </div>
    </aside>
  );
}
