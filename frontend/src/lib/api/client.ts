import type { ApiErrorBody, ApiUser, TokenResponse } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

let accessToken: string | null = null;
let refreshPromise: Promise<TokenResponse | null> | null = null;
const sessionListeners = new Set<(session: TokenResponse | null) => void>();

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly requestId: string | null,
    public readonly body: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions extends Omit<RequestInit, "headers"> {
  auth?: boolean;
  headers?: HeadersInit;
  retryAuth?: boolean;
}

function publishSession(session: TokenResponse | null) {
  accessToken = session?.access_token ?? null;
  sessionListeners.forEach((listener) => listener(session));
}

export function subscribeToSession(
  listener: (session: TokenResponse | null) => void,
) {
  sessionListeners.add(listener);
  return () => sessionListeners.delete(listener);
}

export function clearAccessToken() {
  publishSession(null);
}

export function getAccessToken() {
  return accessToken;
}

function errorMessage(body: unknown, status: number) {
  const detail = (body as ApiErrorBody | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).filter(Boolean).join("; ");
  }
  return `Request failed with status ${status}`;
}

async function rawRequest<T>(path: string, options: RequestOptions = {}) {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (options.auth !== false && accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });
  const body = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      errorMessage(body, response.status),
      response.headers.get("X-Request-ID"),
      body,
    );
  }
  return body as T;
}

async function withBrowserRefreshLock<T>(callback: () => Promise<T>) {
  if (typeof navigator !== "undefined" && navigator.locks) {
    return navigator.locks.request("ai-soc-refresh", callback);
  }
  return callback();
}

async function performRefresh() {
  try {
    const session = await rawRequest<TokenResponse>("/auth/refresh", {
      method: "POST",
      auth: false,
      retryAuth: false,
    });
    publishSession(session);
    return session;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      publishSession(null);
      return null;
    }
    throw error;
  }
}

export function refreshSession() {
  if (!refreshPromise) {
    refreshPromise = withBrowserRefreshLock(performRefresh).finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  try {
    return await rawRequest<T>(path, options);
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status === 401 &&
      options.auth !== false &&
      options.retryAuth !== false
    ) {
      const session = await refreshSession();
      if (session) {
        return rawRequest<T>(path, { ...options, retryAuth: false });
      }
    }
    throw error;
  }
}

export async function loginSession(email: string, password: string) {
  const form = new URLSearchParams({ username: email, password });
  const session = await rawRequest<TokenResponse>("/auth/login", {
    method: "POST",
    auth: false,
    retryAuth: false,
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });
  publishSession(session);
  return session;
}

export async function logoutSession() {
  try {
    await rawRequest("/auth/logout", {
      method: "POST",
      auth: false,
      retryAuth: false,
    });
  } finally {
    publishSession(null);
  }
}

export function getCurrentUser() {
  return apiRequest<ApiUser>("/auth/me");
}

export function resetApiClientForTests() {
  accessToken = null;
  refreshPromise = null;
  sessionListeners.clear();
}
