import type { DocumentTask } from "@/features/documents/documents.types";
import type { AsyncStatus } from "@/types/app";

export function isDocumentTaskTerminal(status: AsyncStatus) {
  return status === "done" || status === "failed";
}

export function shouldPollDocumentTask(status: AsyncStatus) {
  return status === "pending" || status === "running";
}

export function getDocumentProgressLabel(task: Pick<DocumentTask, "progress">) {
  const completed = task.progress?.completed_chunks;
  const total = task.progress?.total_chunks;

  if (typeof completed === "number" && typeof total === "number") {
    return `${completed} / ${total} chunks`;
  }

  return "处理中";
}

export function buildDocumentSummary(task: Pick<DocumentTask, "result">) {
  return {
    summary: task.result?.summary ?? "",
    bulletPoints: task.result?.bullet_points ?? [],
  };
}
