"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { AnalyticsProvider } from "@/components/providers/AnalyticsProvider";
import { DarkModeProvider } from "@/components/providers/DarkModeProvider";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
            retry: 1,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AnalyticsProvider>
        <DarkModeProvider>{children}</DarkModeProvider>
      </AnalyticsProvider>
    </QueryClientProvider>
  );
}
