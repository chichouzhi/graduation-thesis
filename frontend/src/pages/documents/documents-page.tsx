import { Upload } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useAppStore } from "@/app/store";
import { PageSection } from "@/components/layout/page-section";
import { EmptyState } from "@/components/shared/empty-state";
import { SectionHeading } from "@/components/shared/section-heading";
import { Button } from "@/components/ui/button";
import {
  useDocumentTasksQuery,
  usePollingDocumentTaskQuery,
  useUploadDocumentTaskMutation,
} from "@/features/documents/documents.queries";
import {
  buildDocumentSummary,
  getDocumentProgressLabel,
  isDocumentTaskTerminal,
} from "@/features/documents/documents.utils";
import { getErrorMessage, parseApiError } from "@/lib/api-error";

const taskTypeOptions = [
  { value: "summary", label: "摘要总结" },
  { value: "conclusions", label: "提炼结论" },
  { value: "compare", label: "对比分析" },
] as const;

const languageOptions = [
  { value: "zh", label: "中文" },
  { value: "en", label: "English" },
] as const;

const statusLabels = {
  pending: "待处理",
  running: "处理中",
  done: "已完成",
  failed: "已失败",
} as const;

const currentStageLabels: Record<string, string> = {
  upload_accepted: "上传受理",
  pdf_extract: "PDF 解析",
  chunk_summarizing: "分块总结",
  summarize_chunks: "分块总结",
  aggregate: "聚合结果",
  finalize: "生成最终结果",
  final_result: "最终结果",
};

const errorCodeLabels: Record<string, string> = {
  QUEUE_UNAVAILABLE: "队列暂不可用",
  DOMAIN_ERROR: "处理流程异常",
  LLM_RATE_LIMITED: "模型调用受限",
  POLICY_QUEUE_DEPTH: "系统队列繁忙",
};

function formatStatusLabel(status: keyof typeof statusLabels) {
  return statusLabels[status];
}

function formatTaskTypeLabel(taskType?: "summary" | "conclusions" | "compare") {
  switch (taskType) {
    case "summary":
      return "摘要总结";
    case "conclusions":
      return "提炼结论";
    case "compare":
      return "对比分析";
    default:
      return "未知类型";
  }
}

function formatLanguageLabel(language?: "zh" | "en") {
  switch (language) {
    case "zh":
      return "中文";
    case "en":
      return "英文";
    default:
      return "未知语言";
  }
}

function formatCurrentStageLabel(stage?: string | null, status?: keyof typeof statusLabels) {
  if (!stage) {
    if (status === "done") {
      return "任务已完成";
    }
    if (status === "failed") {
      return "任务已失败";
    }
    return "等待任务开始";
  }

  return currentStageLabels[stage] ?? "处理中";
}

function formatErrorCodeLabel(errorCode?: string | null) {
  if (!errorCode) {
    return "未知错误";
  }

  return errorCodeLabels[errorCode] ?? "未知错误";
}

export function DocumentsPage() {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [preferredTaskId, setPreferredTaskId] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [taskType, setTaskType] = useState<"summary" | "conclusions" | "compare">("summary");
  const [language, setLanguage] = useState<"zh" | "en">("zh");
  const [uploadError, setUploadError] = useState("");
  const [fileInputKey, setFileInputKey] = useState(0);

  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const currentTerm = useAppStore((state) => state.currentTerm);

  const tasksQuery = useDocumentTasksQuery(isAuthenticated);
  const uploadMutation = useUploadDocumentTaskMutation();
  const detailQuery = usePollingDocumentTaskQuery(selectedTaskId, Boolean(selectedTaskId));

  const tasks = useMemo(() => tasksQuery.data?.items ?? [], [tasksQuery.data?.items]);

  useEffect(() => {
    if (!tasks.length) {
      if (selectedTaskId !== null && selectedTaskId !== preferredTaskId) {
        setSelectedTaskId(null);
      }
      return;
    }

    if (preferredTaskId) {
      if (tasks.some((task) => task.id === preferredTaskId)) {
        setPreferredTaskId(null);
      } else {
        if (selectedTaskId !== preferredTaskId) {
          setSelectedTaskId(preferredTaskId);
        }
        return;
      }
    }

    if (selectedTaskId && tasks.some((task) => task.id === selectedTaskId)) {
      return;
    }

    setSelectedTaskId(tasks[0].id);
  }, [preferredTaskId, selectedTaskId, tasks]);

  useEffect(() => {
    if (uploadMutation.data?.id) {
      setSelectedTaskId(uploadMutation.data.id);
      setPreferredTaskId(uploadMutation.data.id);
    }
  }, [uploadMutation.data?.id]);

  const selectedTask = detailQuery.data?.id === selectedTaskId ? detailQuery.data : null;
  const detailErrorMessage = detailQuery.isError
    ? getErrorMessage(detailQuery.error, "暂时无法获取任务详情。")
    : "";
  const summary = selectedTask
    ? buildDocumentSummary(selectedTask.result)
    : { summary: "", bulletPoints: [] };
  const showPendingResult = Boolean(
    selectedTask && !isDocumentTaskTerminal(selectedTask.status),
  );

  function handleUpload() {
    if (!selectedFile || uploadMutation.isPending) {
      return;
    }

    setUploadError("");
    uploadMutation.mutate(
      {
        file: selectedFile,
        termId: currentTerm.id,
        taskType,
        language,
      },
      {
        onSuccess: () => {
          setSelectedFile(null);
          setFileInputKey((currentValue) => currentValue + 1);
        },
        onError: (error) => {
          const parsed = parseApiError(error);
          if (parsed.status === 413) {
            setUploadError("PDF 超出服务端限制，请压缩后重试。");
            return;
          }
          setUploadError(getErrorMessage(error, "上传失败，请稍后重试。"));
        },
      },
    );
  }

  return (
    <div className="page-stack">
      <PageSection className="paper" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <p className="kicker">Document Pipeline</p>
          <h2 style={{ marginTop: 14, fontSize: 30, letterSpacing: "-0.04em" }}>PDF 分析与总结任务</h2>
          <p className="muted small" style={{ marginTop: 10, lineHeight: 1.9 }}>
            上传真实 PDF 后，页面会展示任务列表、轮询中的详情状态，以及最终摘要或失败反馈。
          </p>
        </div>
        <div className="upload-panel">
          <div className="upload-controls">
            <div className="upload-grid">
              <div className="field">
                <label htmlFor="document-upload">选择 PDF</label>
                <input
                  key={fileInputKey}
                  id="document-upload"
                  className="input"
                  type="file"
                  accept="application/pdf"
                  onChange={(event) => {
                    setSelectedFile(event.target.files?.[0] ?? null);
                    setUploadError("");
                  }}
                />
              </div>
              <div className="grid-2">
                <div className="field">
                  <label htmlFor="document-task-type">任务类型</label>
                  <select
                    id="document-task-type"
                    className="upload-select"
                    value={taskType}
                    onChange={(event) => setTaskType(event.target.value as typeof taskType)}
                  >
                    {taskTypeOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="document-language">输出语言</label>
                  <select
                    id="document-language"
                    className="upload-select"
                    value={language}
                    onChange={(event) => setLanguage(event.target.value as typeof language)}
                  >
                    {languageOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="upload-meta">
              <Button
                onClick={handleUpload}
                disabled={!selectedFile || uploadMutation.isPending || !isAuthenticated}
              >
                <Upload size={16} />
                {uploadMutation.isPending ? "上传中..." : "上传 PDF"}
              </Button>
              <p className="muted small" style={{ margin: 0, alignSelf: "center" }}>
                当前学期：{currentTerm.name}
                {selectedFile ? ` · 已选择：${selectedFile.name}` : " · 暂未选择文件"}
              </p>
            </div>
          </div>

          {uploadError ? (
            <p className="small" style={{ margin: 0, color: "var(--danger-foreground)" }}>
              {uploadError}
            </p>
          ) : null}
        </div>
      </PageSection>

      <div className="documents-layout">
        <PageSection className="paper">
          <SectionHeading title="任务列表" description="左侧展示真实任务状态，并支持切换查看详情。" />
          {tasksQuery.isLoading ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState
                title="正在加载任务列表"
                description="文档任务正在同步中，请稍候。"
              />
            </div>
          ) : tasksQuery.isError ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState
                title="任务列表加载失败"
                description={getErrorMessage(tasksQuery.error, "暂时无法获取文档任务。")}
                action={
                  <Button variant="outline" onClick={() => tasksQuery.refetch()}>
                    重试
                  </Button>
                }
              />
            </div>
          ) : tasks.length ? (
            <div className="document-list">
              {tasks.map((task) => {
                const isSelected = task.id === selectedTaskId;

                return (
                  <button
                    key={task.id}
                    type="button"
                    className="document-item"
                    onClick={() => setSelectedTaskId(task.id)}
                    style={{
                      width: "100%",
                      cursor: "pointer",
                      textAlign: "left",
                      borderColor: isSelected ? "rgba(31, 107, 104, 0.34)" : undefined,
                      boxShadow: isSelected ? "var(--shadow-subtle)" : "none",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 12,
                        alignItems: "flex-start",
                      }}
                    >
                      <div>
                        <h3>{task.filename}</h3>
                        <p className="muted small" style={{ marginTop: 10 }}>
                          {formatCurrentStageLabel(task.currentStage, task.status)}
                        </p>
                      </div>
                      <span className={`badge ${task.status}`}>{formatStatusLabel(task.status)}</span>
                    </div>
                    <p className="muted small" style={{ marginTop: 12 }}>
                      {task.resultPreview ?? getDocumentProgressLabel(task.progress)}
                    </p>
                  </button>
                );
              })}
            </div>
          ) : (
            <div style={{ marginTop: 22 }}>
              <EmptyState
                title="暂无文档任务"
                description="上传 PDF 后，这里会显示任务状态和结果预览。"
              />
            </div>
          )}
        </PageSection>

        <PageSection className="paper">
          <SectionHeading title="任务详情" description="右侧详情区展示轮询状态、摘要内容与失败原因。" />
          {!selectedTaskId ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState
                title="尚未选择任务"
                description="从左侧选择一个任务后，这里会显示详细状态和处理结果。"
              />
            </div>
          ) : detailQuery.isLoading && !selectedTask ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState
                title="正在同步任务详情"
                description="系统正在获取最新任务状态，请稍候。"
              />
            </div>
          ) : detailQuery.isError && !selectedTask ? (
            <div style={{ marginTop: 22 }}>
              <EmptyState
                title="任务详情加载失败"
                description={detailErrorMessage}
                action={
                  <Button variant="outline" onClick={() => detailQuery.refetch()}>
                    重试
                  </Button>
                }
              />
            </div>
          ) : selectedTask ? (
            <>
              <div
                className="detail-card"
                style={{
                  marginTop: 22,
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 16,
                  alignItems: "flex-start",
                }}
              >
                <div>
                  <h3>{selectedTask.filename}</h3>
                  <p className="muted small" style={{ marginTop: 10 }}>
                    任务类型：{formatTaskTypeLabel(selectedTask.taskType)} · 输出语言：
                    {formatLanguageLabel(selectedTask.language)}
                  </p>
                </div>
                <span className={`badge ${selectedTask.status}`}>
                  {formatStatusLabel(selectedTask.status)}
                </span>
              </div>

              <div className="detail-stages">
                <div className="detail-card">
                  <p style={{ fontWeight: 600 }}>当前阶段</p>
                  <p className="muted small" style={{ marginTop: 12 }}>
                    {formatCurrentStageLabel(selectedTask.currentStage, selectedTask.status)}
                  </p>
                </div>
                <div className="detail-card">
                  <p style={{ fontWeight: 600 }}>处理进度</p>
                  <p className="muted small" style={{ marginTop: 12 }}>
                    {getDocumentProgressLabel(selectedTask.progress)}
                  </p>
                </div>
              </div>

              {showPendingResult ? (
                <div
                  className="detail-card"
                  style={{ marginTop: 18, background: "rgba(255,255,255,0.92)" }}
                >
                  <h3>结果尚未生成</h3>
                  <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                    当前任务仍在处理中，页面会继续自动同步最新状态。
                  </p>
                </div>
              ) : null}

              {detailErrorMessage ? (
                <div
                  className="detail-card"
                  style={{
                    marginTop: 18,
                    borderColor: "rgba(15, 76, 117, 0.18)",
                    background: "rgba(222, 239, 248, 0.55)",
                  }}
                >
                  <h3>最近一次同步失败</h3>
                  <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                    {detailErrorMessage}
                  </p>
                  <div style={{ marginTop: 14 }}>
                    <Button variant="outline" onClick={() => detailQuery.refetch()}>
                      重新同步
                    </Button>
                  </div>
                </div>
              ) : null}

              {selectedTask.status === "done" ? (
                <div
                  className="detail-card"
                  style={{ marginTop: 18, background: "rgba(255,255,255,0.92)" }}
                >
                  <h3>摘要结果</h3>
                  <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                    {summary.summary || "暂无摘要文本。"}
                  </p>
                  {summary.bulletPoints.length ? (
                    <ul className="summary-points">
                      {summary.bulletPoints.map((point) => (
                        <li key={point}>{point}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}

              {selectedTask.status === "failed" ? (
                <div
                  className="detail-card"
                  style={{
                    marginTop: 18,
                    borderColor: "rgba(141, 40, 58, 0.18)",
                    background: "rgba(251, 225, 229, 0.45)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 16,
                      alignItems: "flex-start",
                    }}
                  >
                    <div>
                      <h3>任务执行失败</h3>
                      <p className="muted small" style={{ marginTop: 12, lineHeight: 1.9 }}>
                        错误类型：{formatErrorCodeLabel(selectedTask.errorCode)}
                      </p>
                      <p
                        className="small"
                        style={{ marginTop: 12, color: "var(--danger-foreground)" }}
                      >
                        {selectedTask.errorMessage ?? "服务端未返回更多错误信息。"}
                      </p>
                    </div>
                    <span className="badge failed">{formatStatusLabel("failed")}</span>
                  </div>
                </div>
              ) : null}
            </>
          ) : (
            <div style={{ marginTop: 22 }}>
              <EmptyState
                title="暂无任务详情"
                description="任务详情尚未返回，请稍后重试。"
              />
            </div>
          )}
        </PageSection>
      </div>
    </div>
  );
}
