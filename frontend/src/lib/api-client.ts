import { supabase } from "./supabase";

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  detail: string;
  payload: unknown;

  constructor(status: number, detail: string, payload: unknown) {
    super(`API ${status}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.payload = payload;
  }
}

async function getAccessToken(): Promise<string | null> {
  if (!supabase) {
    return null;
  }

  const {
    data: { session },
  } = await supabase.auth.getSession();

  return session?.access_token ?? null;
}

function buildUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = await getAccessToken();
  const headers = new Headers(init.headers ?? {});
  headers.set("Accept", "application/json");

  const hasBody = init.body !== undefined && init.body !== null;
  if (hasBody && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(buildUrl(path), {
    ...init,
    headers,
  });

  if (!response.ok) {
    let payload: unknown = null;
    const fallbackDetail = response.statusText || "Request failed";
    let detail: string;

    try {
      payload = await response.json();
      if (payload && typeof payload === "object" && "detail" in payload) {
        const maybePayload = payload as { detail?: unknown };
        detail =
          typeof maybePayload.detail === "string"
            ? maybePayload.detail
            : JSON.stringify(payload);
      } else {
        detail = JSON.stringify(payload);
      }
    } catch {
      detail = fallbackDetail;
    }

    throw new ApiError(response.status, detail, payload);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
