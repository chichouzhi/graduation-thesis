import axios from "axios";

import { clearAuthSession, loadAuthSession } from "@/features/auth/auth.storage";

export const apiClient = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
  withCredentials: true,
});

apiClient.interceptors.request.use((config) => {
  const session = loadAuthSession();

  if (session?.accessToken) {
    config.headers.Authorization = `Bearer ${session.accessToken}`;
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearAuthSession();
    }

    return Promise.reject(error);
  },
);
