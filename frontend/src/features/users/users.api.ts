import { apiClient } from "@/lib/axios";
import type {
  PatchUserMeRequest,
  UserMeDto,
} from "@/features/users/users.types";
import { mapUserMeDto } from "@/features/users/users.types";

export async function getUserMe() {
  const response = await apiClient.get<UserMeDto>("/users/me");
  return mapUserMeDto(response.data);
}

export async function patchUserMe(payload: PatchUserMeRequest) {
  const response = await apiClient.patch<UserMeDto>("/users/me", payload);
  return mapUserMeDto(response.data);
}
