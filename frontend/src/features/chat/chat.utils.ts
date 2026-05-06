import type { AsyncTaskStatus } from "@/features/chat/chat.types";

export function isAsyncTaskTerminal(status: AsyncTaskStatus) {
  return status === "done" || status === "failed";
}

export function shouldPollChatJob(status: AsyncTaskStatus) {
  return status === "pending" || status === "running";
}
