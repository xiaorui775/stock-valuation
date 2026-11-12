/** API 客户端：统一解包响应包、错误处理与 401 跳转。 */

export interface Meta {
  source: string | null;
  as_of: string | null;
  cached: boolean;
  stale: boolean;
  missing_fields: string[];
  currency: string | null;
}

export interface ApiEnvelope<T> {
  data: T;
  meta: Meta;
}

export class ApiError extends Error {
  code: string;
  status: number;
  details: Record<string, unknown>;
  requestId: string | null;

  constructor(
    code: string,
    message: string,
    status: number,
    details: Record<string, unknown> = {},
    requestId: string | null = null,
  ) {
    super(message);
    this.code = code;
    this.status = status;
    this.details = details;
    this.requestId = requestId;
  }
}

const BASE = "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<ApiEnvelope<T>> {
  const resp = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });

  const text = await resp.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }

  if (!resp.ok) {
    const err = (payload as { error?: { code?: string; message?: string; details?: Record<string, unknown>; request_id?: string } })
      ?.error;
    if (resp.status === 401 && typeof window !== "undefined") {
      window.location.assign("/login");
    }
    throw new ApiError(
      err?.code ?? "UNKNOWN",
      err?.message ?? `请求失败（${resp.status}）`,
      resp.status,
      err?.details ?? {},
      err?.request_id ?? null,
    );
  }

  return payload as ApiEnvelope<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body === undefined ? undefined : JSON.stringify(body) }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
