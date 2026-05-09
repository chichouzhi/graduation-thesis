import { apiClient } from "@/lib/axios";
import type {
  DocumentTaskDto,
  DocumentTaskListItem,
  DocumentTaskListItemDto,
  PaginatedResponseDto,
  UploadDocumentPayload,
} from "@/features/documents/documents.types";
import {
  mapDocumentTaskDto,
  mapDocumentTaskListItemDto,
  mapPaginatedResponseDto,
} from "@/features/documents/documents.types";

export async function getDocumentTasks() {
  const response = await apiClient.get<PaginatedResponseDto<DocumentTaskListItemDto>>(
    "/document-tasks",
    {
      params: {
        page: 1,
        page_size: 50,
      },
    },
  );

  return mapPaginatedResponseDto<DocumentTaskListItemDto, DocumentTaskListItem>(
    response.data,
    mapDocumentTaskListItemDto,
  );
}

export async function getDocumentTask(taskId: string) {
  const response = await apiClient.get<DocumentTaskDto>(`/document-tasks/${taskId}`);
  return mapDocumentTaskDto(response.data);
}

export async function uploadDocumentTask(payload: UploadDocumentPayload) {
  const formData = new FormData();
  formData.append("file", payload.file);
  formData.append("term_id", payload.termId);
  formData.append("task_type", payload.taskType);
  formData.append("language", payload.language);

  const response = await apiClient.post<DocumentTaskDto>("/document-tasks", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return mapDocumentTaskDto(response.data);
}
