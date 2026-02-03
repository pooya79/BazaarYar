import type { ApiError } from "./types";
import { env } from "./schemas/env";

type HttpOptions = RequestInit & {
  authToken?: string;
  forwardAuthHeader?: string | null;
};

const baseUrl = env.NEXT_PUBLIC_API_BASE_URL.replace(/\/$/, "");

const jsonHeaders = {
  Accept: "application/json",
  "Content-Type": "application/json",
};

const buildUrl = (path: string) =>
  `${baseUrl}${path.startsWith("/") ? "" : "/"}${path}`;

const normalizeError = (response: Response, payload: unknown): ApiError => {
  if (payload && typeof payload === "object" && "detail" in payload) {
    return {
      status: response.status,
      message: String((payload as { detail: unknown }).detail),
      details: payload,
    };
  }

  return {
    status: response.status,
    message: response.statusText || "Request failed",
    details: payload,
  };
};

const mergeHeaders = (options: HttpOptions) => {
  const headers = new Headers(options.headers ?? {});

  if (!headers.has("Accept")) {
    headers.set("Accept", jsonHeaders.Accept);
  }

  const hasBody = Boolean(options.body);
  const isForm = typeof FormData !== "undefined" && options.body instanceof FormData;
  if (hasBody && !isForm && !headers.has("Content-Type")) {
    headers.set("Content-Type", jsonHeaders["Content-Type"]);
  }

  if (options.authToken) {
    headers.set("Authorization", `Bearer ${options.authToken}`);
  } else if (options.forwardAuthHeader) {
    headers.set("Authorization", options.forwardAuthHeader);
  }

  return headers;
};

export async function http<T>(
  path: string,
  options: HttpOptions = {},
): Promise<T> {
  const response = await fetch(buildUrl(path), {
    ...options,
    headers: mergeHeaders(options),
  });

  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    throw normalizeError(response, payload);
  }

  return payload as T;
}

export { buildUrl, normalizeError };
