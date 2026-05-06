import { apiClient } from "@/lib/axios";
import type {
  ChatJob,
  Conversation,
  Message,
  PaginatedResponse,
} from "@/features/chat/chat.types";

export type CreateConversationPayload = {
  term_id: string;
  title?: string;
  context_type?: "general" | "topic" | "document";
  context_ref_id?: string | null;
};

export type PostMessagePayload = {
  content: string;
  client_request_id?: string;
  seq?: number;
};

export type PostMessageResponse = {
  job_id: string;
  user_message: Message;
  assistant_message: Message;
};

export async function getConversations() {
  const response = await apiClient.get<PaginatedResponse<Conversation>>("/conversations");
  return response.data;
}

export async function createConversation(payload: CreateConversationPayload) {
  const response = await apiClient.post<Conversation>("/conversations", payload);
  return response.data;
}

export async function getMessages(conversationId: string) {
  const response = await apiClient.get<PaginatedResponse<Message>>(
    `/conversations/${conversationId}/messages`,
    {
      params: {
        page: 1,
        page_size: 100,
        order: "asc",
      },
    },
  );

  return response.data;
}

export async function postMessage(conversationId: string, payload: PostMessagePayload) {
  const response = await apiClient.post<PostMessageResponse>(
    `/conversations/${conversationId}/messages`,
    payload,
  );

  return response.data;
}

export async function getChatJob(jobId: string) {
  const response = await apiClient.get<ChatJob>(`/chat/jobs/${jobId}`);
  return response.data;
}
