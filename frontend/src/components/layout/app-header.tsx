import { BellDot, GraduationCap, LogOut } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAppStore } from "@/app/store";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";

const pageCopy: Record<string, { title: string; description: string }> = {
  "/app/dashboard": {
    title: "工作台",
    description: "查看近期工作、任务状态和最近活动。",
  },
  "/app/chat": {
    title: "AI 对话",
    description: "围绕课题、论文与实现问题进行异步 AI 对话。",
  },
  "/app/documents": {
    title: "文档分析",
    description: "管理 PDF 分析任务、处理中状态与结果摘要。",
  },
  "/app/topics": {
    title: "选题中心",
    description: "浏览题目、生成教师分析，并组织学生推荐思路。",
  },
  "/app/taskboard": {
    title: "任务看板",
    description: "跟踪毕业设计各阶段任务与关键节点。",
  },
};

export function AppHeader() {
  const location = useLocation();
  const navigate = useNavigate();
  const { currentTerm, currentUser, logout } = useAppStore();
  const current = pageCopy[location.pathname] ?? pageCopy["/app/dashboard"];
  const avatarLabel =
    currentUser?.display_name?.slice(-2) ?? currentUser?.username?.slice(-2) ?? "访客";

  return (
    <header className="app-header">
      <div>
        <h1>{current.title}</h1>
        <p>{current.description}</p>
      </div>

      <div className="header-meta">
        <Badge>
          <GraduationCap size={14} />
          {currentTerm.name}
        </Badge>
        <Badge variant="outline">学生视角</Badge>
        <button className="icon-button" aria-label="查看通知">
          <BellDot size={18} />
        </button>
        <button
          type="button"
          className="logout-button"
          onClick={() => {
            logout();
            navigate("/login", { replace: true });
          }}
        >
          <LogOut size={16} />
          <span>退出</span>
        </button>
        <Avatar>
          <AvatarFallback>{avatarLabel}</AvatarFallback>
        </Avatar>
      </div>
    </header>
  );
}
