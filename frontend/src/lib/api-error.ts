import { isAxiosError } from "axios";

export type ApiErrorInfo = {
  code?: string;
  message: string;
  details?: Record<string, unknown>;
  status?: number;
};

type ErrorEnvelope = {
  error?: {
    code?: string;
    message?: string;
    details?: Record<string, unknown>;
  };
};

export function parseApiError(error: unknown): ApiErrorInfo {
  if (isAxiosError(error)) {
    const envelope = error.response?.data as ErrorEnvelope | undefined;

    return {
      code: envelope?.error?.code,
      message: envelope?.error?.message ?? error.message,
      details: envelope?.error?.details,
      status: error.response?.status,
    };
  }

  if (error instanceof Error) {
    return {
      message: error.message,
    };
  }

  return {
    message: "unknown error",
  };
}

export function getErrorMessage(error: unknown, fallback: string) {
  const parsed = parseApiError(error);

  return parsed.message || fallback;
}
