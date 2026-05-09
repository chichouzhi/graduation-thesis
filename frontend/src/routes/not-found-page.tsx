import { ArrowLeft, Home } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div className="auth-layout">
      <section className="auth-hero">
        <p className="kicker">Route Recovery</p>
        <h1 className="auth-title">找不到这个工作台页面</h1>
        <p className="auth-copy">
          地址可能输入有误，或者该页面尚未开放。你可以返回登录页，也可以回到学生工作台继续操作。
        </p>
      </section>

      <Card className="auth-panel">
        <CardContent>
          <p className="kicker">404 Not Found</p>
          <h2 style={{ marginTop: 18, fontSize: 30, letterSpacing: "-0.04em" }}>
            页面没有找到
          </h2>
          <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
            为了不打断答辩演示流程，系统已提供安全返回入口。
          </p>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 22 }}>
            <Button onClick={() => navigate("/app/dashboard", { replace: true })}>
              <Home size={16} />
              返回工作台
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
