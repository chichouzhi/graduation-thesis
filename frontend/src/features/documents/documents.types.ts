import type { AsyncStatus } from "@/types/app";

export type DocumentTaskType = "summary" | "conclusions" | "compare";
export type DocumentLanguage = "zh" | "en";

export type PaginatedResponseDto<T> = {
  page: number;
  page_size: number;
  total: number;
  items: T[];
};

export type PaginatedResponse<T> = {
  page: number;
  pageSize: number;
  total: number;
  items: T[];
};

export type DocumentTaskProgressDto = {
  completed_chunks?: number;
  total_chunks?: number;
} & Record<string, unknown>;

export type DocumentTaskProgressView = {
  completedChunks?: number;
  totalChunks?: number;
};

export type DocumentTaskProgress = DocumentTaskProgressView;

export type DocumentTaskResultDto = {
  summary?: string;
  bullet_points?: string[];
  raw_model?: string;
} | null;

export type DocumentTaskResult = {
  summary: string;
  bulletPoints: string[];
  rawModel?: string;
} | null;

export type DocumentSummaryView = {
  summary: string;
  bulletPoints: string[];
};

export type DocumentArtifactRefDto = {
  id?: string;
  artifact_type?: string;
  stage?: string;
  chunk_index?: number | null;
  storage_uri?: string | null;
  payload?: Record<string, unknown> | null;
};

export type DocumentArtifactRef = {
  id?: string;
  artifactType?: string;
  stage?: string;
  chunkIndex?: number | null;
  storageUri?: string | null;
  payload?: Record<string, unknown> | null;
};

export type DocumentTaskListItemDto = {
  id: string;
  term_id: string;
  status: AsyncStatus;
  filename: string;
  current_stage?: string | null;
  progress?: DocumentTaskProgressDto;
  task_type?: DocumentTaskType;
  created_at: string;
  updated_at?: string;
  retry_count?: number | null;
  result_preview?: string | null;
};

export type DocumentTaskListItem = {
  id: string;
  termId: string;
  status: AsyncStatus;
  filename: string;
  currentStage?: string | null;
  progress?: DocumentTaskProgress;
  taskType?: DocumentTaskType;
  createdAt: string;
  updatedAt?: string;
  retryCount?: number | null;
  resultPreview?: string | null;
};

export type DocumentTaskDto = {
  id: string;
  term_id: string;
  status: AsyncStatus;
  filename: string;
  task_type: DocumentTaskType;
  language: DocumentLanguage;
  current_stage?: string | null;
  progress?: DocumentTaskProgressDto;
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

export type DocumentTask = {
  id: string;
  termId: string;
  status: AsyncStatus;
  filename: string;
  taskType: DocumentTaskType;
  language: DocumentLanguage;
  currentStage?: string | null;
  progress?: DocumentTaskProgress;
  artifacts: DocumentArtifactRef[];
  lockedAt?: string | null;
  lastCompletedChunk?: number | null;
  createdAt: string;
  updatedAt: string;
  result?: DocumentTaskResult;
  resultStorageUri?: string | null;
  errorCode?: string | null;
  errorMessage?: string | null;
  retryCount: number;
  maxAttempts?: number | null;
  nextRetryAt?: string | null;
};

export type UploadDocumentPayload = {
  file: File;
  termId: string;
  taskType: DocumentTaskType;
  language: DocumentLanguage;
};

export function mapPaginatedResponseDto<TDto, TModel>(
  response: PaginatedResponseDto<TDto>,
  mapItem: (item: TDto) => TModel,
): PaginatedResponse<TModel> {
  return {
    page: response.page,
    pageSize: response.page_size,
    total: response.total,
    items: response.items.map(mapItem),
  };
}

export function mapDocumentTaskProgressDto(
  progress?: DocumentTaskProgressDto,
): DocumentTaskProgress | undefined {
  if (!progress) {
    return undefined;
  }

  return {
    completedChunks: progress.completed_chunks,
    totalChunks: progress.total_chunks,
  };
}

export function mapDocumentTaskResultDto(
  result?: DocumentTaskResultDto,
): DocumentTaskResult | undefined {
  if (result === undefined) {
    return undefined;
  }

  if (result === null) {
    return null;
  }

  return {
    summary: result.summary ?? "",
    bulletPoints: result.bullet_points ?? [],
    rawModel: result.raw_model,
  };
}

export function mapDocumentArtifactRefDto(
  artifact: DocumentArtifactRefDto,
): DocumentArtifactRef {
  return {
    id: artifact.id,
    artifactType: artifact.artifact_type,
    stage: artifact.stage,
    chunkIndex: artifact.chunk_index,
    storageUri: artifact.storage_uri,
    payload: artifact.payload,
  };
}

export function mapDocumentTaskListItemDto(
  task: DocumentTaskListItemDto,
): DocumentTaskListItem {
  return {
    id: task.id,
    termId: task.term_id,
    status: task.status,
    filename: task.filename,
    currentStage: task.current_stage,
    progress: mapDocumentTaskProgressDto(task.progress),
    taskType: task.task_type,
    createdAt: task.created_at,
    updatedAt: task.updated_at,
    retryCount: task.retry_count,
    resultPreview: task.result_preview,
  };
}

export function mapDocumentTaskDto(task: DocumentTaskDto): DocumentTask {
  return {
    id: task.id,
    termId: task.term_id,
    status: task.status,
    filename: task.filename,
    taskType: task.task_type,
    language: task.language,
    currentStage: task.current_stage,
    progress: mapDocumentTaskProgressDto(task.progress),
    artifacts: task.artifacts.map(mapDocumentArtifactRefDto),
    lockedAt: task.locked_at,
    lastCompletedChunk: task.last_completed_chunk,
    createdAt: task.created_at,
    updatedAt: task.updated_at,
    result: mapDocumentTaskResultDto(task.result),
    resultStorageUri: task.result_storage_uri,
    errorCode: task.error_code,
    errorMessage: task.error_message,
    retryCount: task.retry_count,
    maxAttempts: task.max_attempts,
    nextRetryAt: task.next_retry_at,
  };
}
