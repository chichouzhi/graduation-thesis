import { BookOpenText, Files, LayoutDashboard, MessagesSquare, SquareKanban } from "lucide-react";
import { NavLink } from "react-router-dom";

import { cn } from "@/lib/utils";

const items = [
  { to: "/app/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/app/chat", label: "Chat", icon: MessagesSquare },
  { to: "/app/documents", label: "Documents", icon: Files },
  { to: "/app/topics", label: "Topics", icon: BookOpenText },
  { to: "/app/taskboard", label: "Taskboard", icon: SquareKanban },
];

export function AppSidebar() {
  return (
    <aside className="app-sidebar">
      <div>
        <p className="brand-kicker">Academic Copilot</p>
        <h1 className="brand-title">AI 学术助手工作台</h1>
        <p className="brand-text">围绕聊天、文档与毕业任务推进的学生端工作空间。</p>
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
        <strong>当前聚焦：毕业设计推进与答辩准备</strong>
      </div>
    </aside>
  );
}
