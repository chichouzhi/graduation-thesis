import type {
  DocumentSummaryView,
  DocumentTaskProgressView,
} from "@/features/documents/documents.types";
import type { AsyncStatus } from "@/types/app";

export function isDocumentTaskTerminal(status: AsyncStatus) {
  return status === "done" || status === "failed";
}

export function shouldPollDocumentTask(status: AsyncStatus) {
  return status === "pending" || status === "running";
}

export function getDocumentProgressLabel(progress?: DocumentTaskProgressView | null) {
  const completed = progress?.completedChunks;
  const total = progress?.totalChunks;

  if (typeof completed === "number" && typeof total === "number") {
    return `${completed} / ${total} chunks`;
  }

  return "处理中";
}

export function buildDocumentSummary(
  result?: DocumentSummaryView | null,
): DocumentSummaryView {
  return {
    summary: result?.summary ?? "",
    bulletPoints: result?.bulletPoints ?? [],
  };
}
