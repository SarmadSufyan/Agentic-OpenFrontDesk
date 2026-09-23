// Thin client for the OpenFrontDesk API. Auth is a bearer token kept in localStorage (the API
// allows any origin and uses no cookies), refreshed transparently once when a request gets a 401.

import type { TokenOut } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

const ACCESS_KEY = "ofd_token";
const REFRESH_KEY = "ofd_refresh";
const listeners = new Set<() => void>();

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function notify() {
  listeners.forEach((fn) => fn());
}

export const tokenStore = {
  getAccess: () => read(ACCESS_KEY),
  getRefresh: () => read(REFRESH_KEY),
  set(t: Pick<TokenOut, "access_token" | "refresh_token">) {
    try {
      localStorage.setItem(ACCESS_KEY, t.access_token);
      localStorage.setItem(REFRESH_KEY, t.refresh_token);
    } catch {
      /* private mode: the session still works until reload */
    }
    notify();
  },
  clear() {
    try {
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
    } catch {
      /* ignore */
    }
    notify();
  },
  subscribe(fn: () => void) {
    listeners.add(fn);
    const onStorage = (e: StorageEvent) => {
      if (e.key === ACCESS_KEY || e.key === null) fn();
    };
    window.addEventListener("storage", onStorage);
    return () => {
      listeners.delete(fn);
      window.removeEventListener("storage", onStorage);
    };
  },
};

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function errorFrom(res: Response): Promise<ApiError> {
  let message = `Request failed (${res.status})`;
  let code: string | undefined;
  try {
    const j = await res.json();
    if (j?.error?.message) {
      message = j.error.message;
      code = j.error.code;
    } else if (Array.isArray(j?.detail) && j.detail[0]?.msg) {
      message = String(j.detail[0].msg).replace(/^Value error, /, "");
    } else if (typeof j?.detail === "string") {
      message = j.detail;
    }
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(message, res.status, code);
}

let refreshing: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const refresh = tokenStore.getRefresh();
  if (!refresh) return false;
  refreshing ??= (async () => {
    try {
      const res = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) return false;
      tokenStore.set((await res.json()) as TokenOut);
      return true;
    } catch {
      return false;
    } finally {
      setTimeout(() => (refreshing = null), 0);
    }
  })();
  return refreshing;
}

type Options = { method?: string; body?: unknown; form?: FormData; auth?: boolean; keepalive?: boolean };

export async function request<T>(path: string, opts: Options = {}, retried = false): Promise<T> {
  const { method = "GET", body, form, auth = true, keepalive } = opts;
  const headers: Record<string, string> = {};
  if (!form) headers["Content-Type"] = "application/json";
  const token = auth ? tokenStore.getAccess() : null;
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      keepalive,
      body: form ?? (body === undefined ? undefined : JSON.stringify(body)),
    });
  } catch {
    throw new ApiError("Cannot reach the OpenFrontDesk API. Is the backend running?", 0, "network");
  }

  if (res.status === 401 && auth && token && !retried) {
    if (await refreshTokens()) return request<T>(path, opts, true);
    tokenStore.clear();
  }
  if (!res.ok) throw await errorFrom(res);
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown, auth = true) => request<T>(path, { method: "POST", body, auth }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  del: <T = void>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", form }),
};

/** SWR fetcher: keys are API paths. */
export const fetcher = <T>(path: string) => api.get<T>(path);
