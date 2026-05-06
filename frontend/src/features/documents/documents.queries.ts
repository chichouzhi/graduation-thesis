import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getDocumentTask,
  getDocumentTasks,
  uploadDocumentTask,
} from "@/features/documents/documents.api";
import type {
  DocumentTask,
  UploadDocumentPayload,
} from "@/features/documents/documents.types";
import { shouldPollDocumentTask } from "@/features/documents/documents.utils";

export const documentKeys = {
  all: ["documents"] as const,
  list: () => [...documentKeys.all, "list"] as const,
  detail: (taskId: string) => [...documentKeys.all, "detail", taskId] as const,
};

export function useDocumentTasksQuery(enabled: boolean) {
  return useQuery({
    queryKey: documentKeys.list(),
    queryFn: getDocumentTasks,
    enabled,
  });
}

export function useDocumentTaskQuery(taskId: string | null, enabled: boolean) {
  return useQuery<DocumentTask>({
    queryKey: taskId
      ? documentKeys.detail(taskId)
      : [...documentKeys.all, "detail", "empty"],
    queryFn: async () => getDocumentTask(taskId!),
    enabled: enabled && Boolean(taskId),
  });
}

export function useUploadDocumentTaskMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: UploadDocumentPayload) => uploadDocumentTask(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: documentKeys.list(),
      });
    },
  });
}

export function usePollingDocumentTaskQuery(taskId: string | null, enabled: boolean) {
  const queryClient = useQueryClient();

  return useQuery<DocumentTask>({
    queryKey: taskId
      ? documentKeys.detail(taskId)
      : [...documentKeys.all, "detail", "empty"],
    queryFn: async () => {
      const task = await getDocumentTask(taskId!);
      await queryClient.invalidateQueries({
        queryKey: documentKeys.list(),
      });
      return task;
    },
    enabled: enabled && Boolean(taskId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && shouldPollDocumentTask(status) ? 2000 : false;
    },
    refetchIntervalInBackground: false,
    retry: false,
    staleTime: 0,
    gcTime: 0,
  });
}
