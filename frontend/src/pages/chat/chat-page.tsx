import { SendHorizonal } from "lucide-react";

import { PageSection } from "@/components/layout/page-section";
import { SectionHeading } from "@/components/shared/section-heading";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { conversations, messages } from "@/features/chat/chat.mock";

export function ChatPage() {
  return (
    <div className="chat-layout">
      <PageSection className="paper">
        <SectionHeading title="会话列表" description="预留后续会话拉取与切换能力。" />
        <div className="conversation-list">
          {conversations.map((item) => (
            <div key={item.id} className="conversation-item">
              <h3>{item.title}</h3>
              <p className="muted small" style={{ marginTop: 10 }}>
                更新于 {item.updatedAt}
              </p>
            </div>
          ))}
        </div>
      </PageSection>

      <PageSection className="paper chat-main">
        <SectionHeading title="消息流" description="天然预留 assistant 异步状态显示与后续轮询空间。" />
        <ScrollArea style={{ marginTop: 22, flex: 1 }}>
          <div className="message-list">
            {messages.map((message) => (
              <div key={message.id} className={`message-card ${message.role}`}>
                <div className="message-meta">
                  <span className="message-role">{message.role}</span>
                  {message.status ? <StatusBadge status={message.status} /> : null}
                </div>
                <p className="message-content">{message.content || "等待任务受理后生成内容…"}</p>
              </div>
            ))}
          </div>
        </ScrollArea>
        <div className="chat-input">
          <Input placeholder="输入你想继续推进的问题…" />
          <Button aria-label="发送消息" className="h-12 w-12 rounded-[18px] p-0">
            <SendHorizonal size={18} />
          </Button>
        </div>
      </PageSection>

      <PageSection className="paper">
        <SectionHeading title="当前会话摘要" description="这里预留 job 状态、上下文与观察面板。" />
        <div className="detail-stages" style={{ marginTop: 22 }}>
          <div className="detail-card">
            <p style={{ fontWeight: 600 }}>上下文类型</p>
            <p className="muted small" style={{ marginTop: 10 }}>
              general
            </p>
          </div>
          <div className="detail-card">
            <p style={{ fontWeight: 600 }}>异步说明</p>
            <p className="muted small" style={{ marginTop: 10 }}>
              下一轮这里可以展示 `job_id`、最近一次状态变化和失败原因。
            </p>
          </div>
        </div>
      </PageSection>
    </div>
  );
}
