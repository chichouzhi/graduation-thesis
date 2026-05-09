import { useMutation, useQuery } from "@tanstack/react-query";

import { getUserMe, patchUserMe } from "@/features/users/users.api";

export const userKeys = {
  me: ["users", "me"] as const,
};

export function useUserMeQuery(enabled: boolean) {
  return useQuery({
    queryKey: userKeys.me,
    queryFn: getUserMe,
    enabled,
  });
}

export function useUpdateUserMeMutation() {
  return useMutation({
    mutationFn: patchUserMe,
  });
}
