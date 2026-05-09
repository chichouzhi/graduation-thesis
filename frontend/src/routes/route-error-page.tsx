import { AlertTriangle, ArrowLeft, RotateCcw } from "lucide-react";
import { isRouteErrorResponse, useNavigate, useRouteError } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

function getRouteErrorCopy(error: unknown) {
  if (isRouteErrorResponse(error)) {
    if (error.status === 404) {
      return {
        title: "页面没有找到",
        description: "当前地址没有对应的工作台页面，可以返回登录页后重新进入。",
      };
    }

    return {
      title: "页面加载失败",
      description: `请求返回 ${error.status}，请稍后重试或返回入口页。`,
    };
  }

  return {
    title: "工作台暂时遇到问题",
    description: "系统已经拦截到页面异常，没有暴露技术错误。请刷新页面或返回登录页重新进入。",
  };
}

export function RouteErrorPage() {
  const navigate = useNavigate();
  const error = useRouteError();
  const copy = getRouteErrorCopy(error);

  return (
    <div className="auth-layout">
      <section className="auth-hero">
        <p className="kicker">Workspace Recovery</p>
        <h1 className="auth-title">AI 学术助手工作台</h1>
        <p className="auth-copy">
          页面异常不应该打断学生演示流程。这里提供安全返回和刷新入口，方便继续完成毕业设计工作。
        </p>
      </section>

      <Card className="auth-panel">
        <CardContent>
          <div className="icon-pill">
            <AlertTriangle size={20} />
          </div>
          <h2 style={{ marginTop: 18, fontSize: 30, letterSpacing: "-0.04em" }}>
            {copy.title}
          </h2>
          <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
            {copy.description}
          </p>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 22 }}>
            <Button onClick={() => window.location.reload()}>
              <RotateCcw size={16} />
              刷新页面
            </Button>
            <Button variant="outline" onClick={() => navigate("/login", { replace: true })}>
              <ArrowLeft size={16} />
              返回登录页
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
