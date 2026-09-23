"use client";

import { SWRConfig } from "swr";

import { TooltipProvider } from "@/components/ui/tooltip";
import { ApiError, fetcher } from "@/lib/api";
import { AuthProvider } from "@/lib/auth";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SWRConfig
      value={{
        fetcher,
        // Do not hammer the API on auth or validation errors; only transient failures retry.
        shouldRetryOnError: (err) => !(err instanceof ApiError) || err.status >= 500 || err.status === 0,
        errorRetryCount: 3,
      }}
    >
      <AuthProvider>
        <TooltipProvider>{children}</TooltipProvider>
      </AuthProvider>
    </SWRConfig>
  );
}
