export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

let unauthenticated: (() => void) | undefined;
export function onUnauthenticated(callback: () => void) {
  unauthenticated = callback;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    credentials: "include",
    ...init,
    headers: {
      ...(init.method && init.method !== "GET" ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });
  if (response.status === 401) unauthenticated?.();
  const data = (await response.json().catch(() => ({}))) as { error?: string };
  if (!response.ok) throw new ApiError(response.status, data.error ?? "אירעה שגיאה");
  return data as T;
}

export const get = <T>(path: string) => api<T>(path);
export const write = <T>(path: string, method: "POST" | "PUT" | "DELETE", body?: unknown) =>
  api<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
