import { BookMarked, KeyRound } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAppStore } from "@/app/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { login as loginRequest } from "@/features/auth/auth.api";
import { getErrorMessage, parseApiError } from "@/lib/api-error";

export function LoginPage() {
  const navigate = useNavigate();
  const login = useAppStore((state) => state.login);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const mutation = useMutation({
    mutationFn: loginRequest,
    onSuccess: (data) => {
      login({
        accessToken: data.access_token,
        expiresIn: data.expires_in,
        user: data.user,
      });
      navigate("/app/dashboard", { replace: true });
    },
    onError: (error) => {
      const parsed = parseApiError(error);
      if (parsed.code === "UNAUTHORIZED") {
        setErrorMessage("用户名或密码错误，请重新输入。");
        return;
      }
      if (parsed.code === "VALIDATION_ERROR") {
        setErrorMessage(parsed.message);
        return;
      }
      setErrorMessage(getErrorMessage(error, "登录失败，请稍后重试。"));
    },
  });

  return (
    <div className="auth-layout">
      <section className="auth-hero">
        <p className="kicker">Academic Copilot</p>
        <h1 className="auth-title">面向毕业设计全过程的 AI 学术助手工作台</h1>
        <p className="auth-copy">
          将异步聊天、文档处理、选题辅助和任务推进整合到同一套学生端工作空间中，帮助学生持续管理毕业设计过程。
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
          <h3>学生端工作入口</h3>
              <p>当前接入真实登录链路，进入后可查看当前学期的任务、文档和选题状态。</p>
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

          <div
            className="detail-card"
            style={{
              marginTop: 18,
              borderColor: "rgba(31, 107, 104, 0.18)",
              background: "rgba(223, 236, 235, 0.56)",
            }}
          >
            <p style={{ fontWeight: 600 }}>答辩演示账号</p>
            <p className="muted small" style={{ marginTop: 10, lineHeight: 1.8 }}>
              演示时可一键填入学生账号，平时保持输入框为空，避免把演示密码直接暴露在首屏。
            </p>
            <Button
              variant="outline"
              style={{ marginTop: 14 }}
              disabled={mutation.isPending}
              onClick={() => {
                setUsername("api-login-user");
                setPassword("correct-pass");
                setErrorMessage("");
              }}
            >
              填入演示账号
            </Button>
          </div>

          <div className="form-stack">
            <div className="field">
              <label htmlFor="student-id">学号或用户名</label>
              <Input
                id="student-id"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                disabled={mutation.isPending}
              />
            </div>
            <div className="field">
              <label htmlFor="password">密码</label>
              <Input
                id="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={mutation.isPending}
                type="password"
              />
            </div>
            {errorMessage ? (
              <p className="small" style={{ color: "var(--danger-foreground)", margin: 0 }}>
                {errorMessage}
              </p>
            ) : null}
            <Button
              className="w-full"
              disabled={mutation.isPending}
              onClick={() => {
                setErrorMessage("");
                mutation.mutate({
                  username: username.trim(),
                  password,
                });
              }}
            >
              {mutation.isPending ? "登录中…" : "进入 AI 学术助手工作台"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
