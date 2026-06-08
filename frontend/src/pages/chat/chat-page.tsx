import { MessageSquarePlus, SendHorizonal } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAppStore } from "@/app/store";
import { PageSection } from "@/components/layout/page-section";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionHeading } from "@/components/shared/section-heading";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  useChatJobQuery,
  useConversationsQuery,
  useCreateConversationMutation,
  useMessagesQuery,
  usePostMessageMutation,
} from "@/features/chat/chat.queries";
import { getErrorMessage } from "@/lib/api-error";

export function ChatPage() {
  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const currentTerm = useAppStore((state) => state.currentTerm);
  const fallbackConversationRequestedRef = useRef(false);

  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [sendError, setSendError] = useState("");

  const conversationsQuery = useConversationsQuery(isAuthenticated);
  const createConversationMutation = useCreateConversationMutation();
  const messagesQuery = useMessagesQuery(selectedConversationId, Boolean(selectedConversationId));
  const postMessageMutation = usePostMessageMutation(selectedConversationId);
  const chatJobQuery = useChatJobQuery(activeJobId, selectedConversationId);

  const conversations = conversationsQuery.data?.items ?? [];
  const createdConversationId = createConversationMutation.data?.id ?? null;
  const createFallbackConversation = createConversationMutation.mutate;
  const isCreatingFallbackConversation = createConversationMutation.isPending;

  useEffect(() => {
    if (conversations.length && !selectedConversationId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedConversationId(conversations[0].id);
    }
  }, [conversations, selectedConversationId]);

  useEffect(() => {
    if (conversations.length > 0) {
      fallbackConversationRequestedRef.current = false;
      return;
    }

    if (
      !conversationsQuery.isSuccess ||
      isCreatingFallbackConversation ||
      createdConversationId ||
      fallbackConversationRequestedRef.current
    ) {
      return;
    }

    fallbackConversationRequestedRef.current = true;
    createFallbackConversation({
        term_id: currentTerm.id,
        title: "通用学术咨询",
        context_type: "general",
      });
  }, [
    conversations.length,
    conversationsQuery.isSuccess,
    createFallbackConversation,
    createdConversationId,
    isCreatingFallbackConversation,
    currentTerm.id,
  ]);

  useEffect(() => {
    if (createdConversationId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedConversationId(createdConversationId);
    }
  }, [createdConversationId]);

  useEffect(() => {
    if (chatJobQuery.data?.status === "done" || chatJobQuery.data?.status === "failed") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setActiveJobId(null);
    }
  }, [chatJobQuery.data?.status]);

  const messages = useMemo(() => {
    const serverMessages = messagesQuery.data?.items ?? [];
    const sendSnapshot = postMessageMutation.data;

    if (!sendSnapshot) {
      return serverMessages;
    }

    const ids = new Set(serverMessages.map((item) => item.id));

    return [
      ...serverMessages,
      ...[sendSnapshot.user_message, sendSnapshot.assistant_message].filter((item) => !ids.has(item.id)),
    ];
  }, [messagesQuery.data?.items, postMessageMutation.data]);

  function handleCreateConversation() {
    createConversationMutation.mutate({
      term_id: currentTerm.id,
      title: "新建学术咨询",
      context_type: "general",
    });
  }

  function handleSend() {
    const content = draft.trim();

    if (!selectedConversationId || !content || postMessageMutation.isPending) {
      return;
    }

    setSendError("");
    postMessageMutation.mutate(
      {
        content,
      },
      {
        onSuccess: (data) => {
          setDraft("");
          setActiveJobId(data.job_id);
        },
        onError: (error) => {
          setSendError(getErrorMessage(error, "消息发送失败，请稍后重试。"));
        },
      },
    );
  }

  return (
    <div className="chat-layout">
      <PageSection className="paper">
        <div className="section-heading-row">
          <SectionHeading title="会话列表" description="已接入真实会话接口，默认进入最近会话。" />
          <Button
            aria-label="新建会话"
            className="h-10 w-10 p-0"
            variant="outline"
            disabled={createConversationMutation.isPending}
            onClick={handleCreateConversation}
            title="新建会话"
          >
            <MessageSquarePlus size={18} />
          </Button>
        </div>
        <div className="conversation-list">
          {conversationsQuery.isLoading ? (
            <EmptyState
              title="正在加载会话"
              description="系统正在读取你的历史会话与当前学期上下文。"
            />
          ) : null}

          {conversationsQuery.isError ? (
            <EmptyState
              title="会话加载失败"
              description={getErrorMessage(conversationsQuery.error, "当前无法读取会话列表。")}
              action={
                <Button variant="outline" onClick={() => void conversationsQuery.refetch()}>
                  重新加载
                </Button>
              }
            />
          ) : null}

          {createConversationMutation.isError ? (
            <EmptyState
              title="默认会话创建失败"
              description={getErrorMessage(
                createConversationMutation.error,
                "尚未能自动创建默认学术咨询会话。",
              )}
              action={
                <Button
                  variant="outline"
                  onClick={() =>
                    createConversationMutation.mutate({
                      term_id: currentTerm.id,
                      title: "通用学术咨询",
                      context_type: "general",
                    })
                  }
                >
                  重试创建
                </Button>
              }
            />
          ) : null}

          {!conversationsQuery.isLoading &&
          !conversationsQuery.isError &&
          !createConversationMutation.isPending &&
          conversations.length === 0 ? (
            <EmptyState
              title="尚无会话"
              description="系统会在首次进入时自动创建一个通用会话。"
            />
          ) : null}

          {conversations.map((item) => (
            <button
              key={item.id}
              type="button"
              className="conversation-item text-left"
              onClick={() => setSelectedConversationId(item.id)}
              style={{
                borderColor:
                  item.id === selectedConversationId ? "rgba(31, 107, 104, 0.34)" : undefined,
                boxShadow: item.id === selectedConversationId ? "var(--shadow-subtle)" : undefined,
              }}
            >
              <h3>{item.title || "未命名会话"}</h3>
              <p className="muted small" style={{ marginTop: 10 }}>
                {item.context_type || "general"} · 更新于 {item.updated_at || item.created_at}
              </p>
            </button>
          ))}
        </div>
      </PageSection>

      <PageSection className="paper chat-main">
        <SectionHeading title="消息流" description="真实消息列表与 assistant 异步状态已经接入。" />
        <ScrollArea style={{ marginTop: 22, flex: 1 }}>
          <div className="message-list">
            {!selectedConversationId && !conversationsQuery.isLoading ? (
              <EmptyState
                title="等待会话就绪"
                description="创建或选择一个会话后，这里会展示真实消息流。"
              />
            ) : null}

            {messagesQuery.isLoading && selectedConversationId ? (
              <EmptyState title="正在加载消息" description="会话历史正在同步到当前工作台。" />
            ) : null}

            {messagesQuery.isError ? (
              <EmptyState
                title="消息加载失败"
                description={getErrorMessage(messagesQuery.error, "当前无法读取消息列表。")}
                action={
                  <Button variant="outline" onClick={() => void messagesQuery.refetch()}>
                    重新加载
                  </Button>
                }
              />
            ) : null}

            {!messagesQuery.isLoading && !messagesQuery.isError && selectedConversationId && messages.length === 0 ? (
              <EmptyState
                title="会话已建立"
                description="可以直接输入问题，开始本学期的学术咨询。"
              />
            ) : null}

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
          <Input
            placeholder="输入你想继续推进的问题…"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                handleSend();
              }
            }}
            disabled={!selectedConversationId || postMessageMutation.isPending}
          />
          <Button
            aria-label="发送消息"
            className="h-12 w-12 rounded-[18px] p-0"
            disabled={!selectedConversationId || !draft.trim() || postMessageMutation.isPending}
            onClick={handleSend}
          >
            <SendHorizonal size={18} />
          </Button>
        </div>
        {sendError ? (
          <p className="small" style={{ color: "var(--danger-foreground)", margin: "12px 4px 0" }}>
            {sendError}
          </p>
        ) : null}
      </PageSection>
    </div>
  );
}
