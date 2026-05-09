import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import type { PropsWithChildren } from "react";

import { useAppStore } from "@/app/store";

export function AppProviders({ children }: PropsWithChildren) {
  const hydrateAuth = useAppStore((state) => state.hydrateAuth);
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  useEffect(() => {
    hydrateAuth();
  }, [hydrateAuth]);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
