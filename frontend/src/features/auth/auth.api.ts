import { apiClient } from "@/lib/axios";
import type { LoginRequest, LoginResponse } from "@/features/auth/auth.types";

export async function login(payload: LoginRequest) {
  const response = await apiClient.post<LoginResponse>("/auth/login", payload);
  return response.data;
}
