"use client";

import useSWR, { useSWRConfig } from "swr";

import { api } from "./api";
import type { Agent, Analytics, KnowledgeDoc, Tenant } from "./types";

export function useTenant() {
  return useSWR<Tenant>("/tenants/current");
}

export function useAgent() {
  return useSWR<Agent>("/agents/current");
}

export function useAnalytics() {
  return useSWR<Analytics>("/analytics/overview");
}

/** Knowledge docs; polls every 2s while anything is still indexing. */
export function useDocs() {
  return useSWR<KnowledgeDoc[]>("/knowledge", {
    refreshInterval: (docs) =>
      docs?.some((d) => d.status === "pending" || d.status === "processing") ? 2000 : 0,
  });
}

/** Merge keys into the workspace settings (the API merges, never replaces) and refresh the cache. */
export function useSaveSettings() {
  const { mutate } = useSWRConfig();
  return async (partial: Record<string, unknown>) => {
    const tenant = await api.patch<Tenant>("/tenants/current", { settings: partial });
    await mutate("/tenants/current", tenant, { revalidate: false });
    return tenant;
  };
}
