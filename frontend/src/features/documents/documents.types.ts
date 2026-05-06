import type { AsyncStatus } from "@/types/app";

export type DocumentTaskType = "summary" | "conclusions" | "compare";
export type DocumentLanguage = "zh" | "en";

export type DocumentTaskProgress = {
  completed_chunks?: number;
  total_chunks?: number;
} & Record<string, unknown>;

export type DocumentTaskResultDto = {
  summary?: string;
  bullet_points?: string[];
  raw_model?: string;
} | null;

export type DocumentTaskResult = DocumentTaskResultDto;

export type DocumentArtifactRefDto = {
  id?: string;
  artifact_type?: string;
  stage?: string;
  chunk_index?: number | null;
  storage_uri?: string | null;
  payload?: Record<string, unknown> | null;
};

export type DocumentArtifactRef = DocumentArtifactRefDto;

export type DocumentTaskListItemDto = {
  id: string;
  term_id: string;
  status: AsyncStatus;
  filename: string;
  current_stage?: string | null;
  progress?: DocumentTaskProgress;
  task_type?: DocumentTaskType;
  created_at: string;
  updated_at?: string;
  retry_count?: number | null;
  result_preview?: string | null;
};

export type DocumentTaskListItem = DocumentTaskListItemDto;

export type DocumentTaskDto = {
  id: string;
  term_id: string;
  status: AsyncStatus;
  filename: string;
  task_type: DocumentTaskType;
  language: DocumentLanguage;
  current_stage?: string | null;
  progress?: DocumentTaskProgress;
  artifacts: DocumentArtifactRefDto[];
  locked_at?: string | null;
  last_completed_chunk?: number | null;
  created_at: string;
  updated_at: string;
  result?: DocumentTaskResultDto;
  result_storage_uri?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  retry_count: number;
  max_attempts?: number | null;
  next_retry_at?: string | null;
};

export type DocumentTask = DocumentTaskDto;

export type UploadDocumentPayload = {
  file: File;
  termId: string;
  taskType: DocumentTaskType;
  language: DocumentLanguage;
};
