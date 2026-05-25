import { API_URL } from "@/lib/config";
import type { BackendError, HttpMethod } from "@/lib/types";

export class RequestError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "RequestError";
    this.status = status;
  }
}

async function handleErrorResponse(res: Response): Promise<never> {
  let data: BackendError = {};
  try {
    data = await res.json();
  } catch {
    data = {};
  }
  throw new RequestError(
    res.status,
    data.message || data.error || data.detail || "Request failed"
  );
}

export async function REQUEST<T>(
  method: HttpMethod,
  url: string,
  body?: unknown,
  options?: { isMultipart?: boolean }
): Promise<T> {
  async function request(): Promise<Response> {
    const headers: Record<string, string> = {};

    if (!options?.isMultipart) {
      headers["Content-Type"] = "application/json";
    }
    if (typeof window !== "undefined") {
      const access = localStorage.getItem("access");
      if (access) {
        headers["Authorization"] = `Bearer ${access}`;
      }
    }
    return fetch(`${API_URL.replace(/\/$/, "")}/api/${url.replace(/^\//, "")}`, {
      method,
      headers,
      body: options?.isMultipart ? (body as BodyInit) : body ? JSON.stringify(body) : null
    });
  }

  const res = await request();
  if (!res.ok) {
    await handleErrorResponse(res);
  }
  return (await res.json()) as T;
}
