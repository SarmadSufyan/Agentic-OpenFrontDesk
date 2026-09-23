"use client";

import { createContext, useCallback, useContext, useMemo, useSyncExternalStore } from "react";
import useSWR, { useSWRConfig } from "swr";

import { api, tokenStore } from "./api";
import type { Me, Membership, TokenOut } from "./types";

// "error": signed in, but the API could not be reached (kept distinct so an outage is not a logout).
type Status = "loading" | "authed" | "anon" | "error";

interface AuthValue {
  status: Status;
  me: Me | undefined;
  workspace: Membership | undefined;
  login: (email: string, password: string) => Promise<void>;
  signup: (input: { email: string; password: string; name?: string; business_name?: string }) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<unknown>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // undefined on the server and during hydration ("unknown"), then the stored token or null.
  const token = useSyncExternalStore(tokenStore.subscribe, tokenStore.getAccess, () => undefined);
  const { mutate } = useSWRConfig();
  const { data: me, error, mutate: refreshMe } = useSWR<Me>(token ? "/auth/me" : null, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  });

  // A 401 clears the stored token (see api.ts), which turns this into "anon".
  const status: Status =
    token === undefined ? "loading" : !token ? "anon" : me ? "authed" : error ? "error" : "loading";

  const login = useCallback(async (email: string, password: string) => {
    tokenStore.set(await api.post<TokenOut>("/auth/login", { email, password }, false));
  }, []);

  const signup = useCallback(
    async (input: { email: string; password: string; name?: string; business_name?: string }) => {
      tokenStore.set(await api.post<TokenOut>("/auth/signup", input, false));
    },
    [],
  );

  const logout = useCallback(() => {
    tokenStore.clear();
    // Drop every cached response so the next account never sees the previous one's data.
    mutate(() => true, undefined, { revalidate: false });
  }, [mutate]);

  const value = useMemo<AuthValue>(
    () => ({
      status,
      me: status === "authed" ? me : undefined,
      workspace: status === "authed" ? me?.memberships[0] : undefined,
      login,
      signup,
      logout,
      refreshMe,
    }),
    [status, me, login, signup, logout, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
