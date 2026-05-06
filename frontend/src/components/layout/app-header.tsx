import { BellDot, GraduationCap } from "lucide-react";
import { useLocation } from "react-router-dom";

import { useAppStore } from "@/app/store";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";

const pageCopy: Record<string, { title: string; description: string }> = {
  "/app/dashboard": {
    title: "Dashboard",
    description: "查看近期工作、任务状态和最近活动。",
  },
  "/app/chat": {
    title: "Chat",
    description: "围绕课题、论文与实现问题进行异步 AI 对话。",
  },
  "/app/documents": {
    title: "Documents",
    description: "管理 PDF 分析任务、处理中状态与结果摘要。",
  },
  "/app/topics": {
    title: "Topics",
    description: "浏览题目方向，组织选题思路与研究重点。",
  },
  "/app/taskboard": {
    title: "Taskboard",
    description: "跟踪毕业设计各阶段任务与关键节点。",
  },
};

export function AppHeader() {
  const location = useLocation();
  const { currentTerm, currentUser } = useAppStore();
  const current = pageCopy[location.pathname] ?? pageCopy["/app/dashboard"];

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
        <Avatar>
          <AvatarFallback>{currentUser.name.slice(-2)}</AvatarFallback>
        </Avatar>
      </div>
    </header>
  );
}
