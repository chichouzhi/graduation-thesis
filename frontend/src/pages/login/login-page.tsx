import { BookMarked, KeyRound } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useAppStore } from "@/app/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export function LoginPage() {
  const navigate = useNavigate();
  const login = useAppStore((state) => state.login);

  return (
    <div className="auth-layout">
      <section className="auth-hero">
        <p className="kicker">Academic Copilot</p>
        <h1 className="auth-title">面向毕业设计全过程的 AI 学术助手工作台</h1>
        <p className="auth-copy">
          将异步聊天、文档处理、选题辅助和任务推进整合到同一套学生端工作空间中，适合演示完整的毕业设计产品链路。
        </p>
        <div className="auth-grid">
          <Card className="auth-card">
            <CardContent>
              <BookMarked size={20} color="var(--primary)" />
              <h3>聚焦学术工作流</h3>
              <p>聊天、文档和阶段任务围绕毕业设计推进自然串联。</p>
            </CardContent>
          </Card>
          <Card className="auth-card">
            <CardContent>
              <KeyRound size={20} color="var(--primary)" />
              <h3>学生端答辩视角</h3>
              <p>本轮使用静态登录入口和假数据，专注建立稳定工作台骨架。</p>
            </CardContent>
          </Card>
        </div>
      </section>

      <Card className="auth-panel">
        <CardContent>
          <p className="kicker">Student Access</p>
          <h2 style={{ marginTop: 18, fontSize: 30, letterSpacing: "-0.04em" }}>登录工作台</h2>
          <p className="muted small" style={{ marginTop: 10 }}>
            使用学生端入口进入当前学期工作空间。
          </p>

          <div className="form-stack">
            <div className="field">
              <label htmlFor="student-id">学号或用户名</label>
              <Input id="student-id" defaultValue="20220001" />
            </div>
            <div className="field">
              <label htmlFor="password">密码</label>
              <Input id="password" defaultValue="demo-password" type="password" />
            </div>
            <Button
              className="w-full"
              onClick={() => {
                login();
                navigate("/app/dashboard");
              }}
            >
              进入 AI 学术助手工作台
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
