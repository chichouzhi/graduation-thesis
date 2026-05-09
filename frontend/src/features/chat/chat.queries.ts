import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createConversation,
  type CreateConversationPayload,
  getChatJob,
  getConversations,
  getMessages,
  postMessage,
  type PostMessagePayload,
} from "@/features/chat/chat.api";
import type { ChatJob } from "@/features/chat/chat.types";
import { shouldPollChatJob } from "@/features/chat/chat.utils";

export const chatKeys = {
  all: ["chat"] as const,
  conversations: () => [...chatKeys.all, "conversations"] as const,
  messages: (conversationId: string) => [...chatKeys.all, "messages", conversationId] as const,
  job: (jobId: string) => [...chatKeys.all, "job", jobId] as const,
};

export function useConversationsQuery(enabled: boolean) {
  return useQuery({
    queryKey: chatKeys.conversations(),
    queryFn: getConversations,
    enabled,
  });
}

export function useMessagesQuery(conversationId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: conversationId ? chatKeys.messages(conversationId) : [...chatKeys.all, "messages", "empty"],
    queryFn: () => getMessages(conversationId!),
    enabled: enabled && Boolean(conversationId),
  });
}

export function useCreateConversationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateConversationPayload) => createConversation(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: chatKeys.conversations(),
      });
    },
  });
}

export function usePostMessageMutation(conversationId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: PostMessagePayload) => postMessage(conversationId!, payload),
    onSuccess: async () => {
      if (conversationId) {
        await queryClient.invalidateQueries({
          queryKey: chatKeys.messages(conversationId),
        });
      }
    },
  });
}

export function useChatJobQuery(jobId: string | null, conversationId: string | null) {
  const queryClient = useQueryClient();

  return useQuery<ChatJob>({
    queryKey: jobId ? chatKeys.job(jobId) : [...chatKeys.all, "job", "empty"],
    queryFn: async () => {
      const job = await getChatJob(jobId!);

      if (conversationId) {
        await queryClient.invalidateQueries({
          queryKey: chatKeys.messages(conversationId),
        });
      }

      return job;
    },
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && shouldPollChatJob(status) ? 2000 : false;
    },
    refetchIntervalInBackground: false,
    retry: false,
    staleTime: 0,
    gcTime: 0,
  });
}
