export type AsyncTaskStatus = "pending" | "running" | "done" | "failed";

export type PaginatedResponse<T> = {
  page: number;
  page_size: number;
  total: number;
  items: T[];
};

export type Conversation = {
  id: string;
  term_id: string;
  title?: string | null;
  context_type?: "general" | "topic" | "document";
  context_ref_id?: string | null;
  created_at: string;
  updated_at?: string;
};

export type Message = {
  id: string;
  conversation_id: string;
  role: "system" | "user" | "assistant";
  content: string;
  status?: AsyncTaskStatus | null;
  created_at: string;
  updated_at?: string;
};

export type ChatJob = {
  job_id: string;
  conversation_id: string;
  user_message_id: string;
  assistant_message_id: string;
  status: AsyncTaskStatus;
  error_code?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
};
