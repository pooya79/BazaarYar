import { buildUrl, normalizeError } from "../http";
import {
  type PromptCreateInput,
  type PromptDetail,
  type PromptSummary,
  type PromptUpdateInput,
  promptCreateInputSchema,
  promptDetailSchema,
  promptSummarySchema,
  promptUpdateInputSchema,
} from "../schemas/prompts";

const parseJsonResponse = async (response: Response): Promise<unknown> => {
  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
};

const requestJson = async (
  path: string,
  options: RequestInit = {},
): Promise<unknown> => {
  const response = await fetch(buildUrl(path), {
    ...options,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  const payload = await parseJsonResponse(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }
  return payload;
};

type ListPromptsOptions = {
  q?: string;
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
};

export async function listPrompts(
  options: ListPromptsOptions = {},
): Promise<PromptSummary[]> {
  const params = new URLSearchParams();
  if (options.q?.trim()) {
    params.set("q", options.q.trim());
  }
  if (typeof options.limit === "number") {
    params.set("limit", String(options.limit));
  }
  if (typeof options.offset === "number") {
    params.set("offset", String(options.offset));
  }
  const query = params.toString();
  const payload = await requestJson(
    query ? `/api/prompts?${query}` : "/api/prompts",
    {
      method: "GET",
      signal: options.signal,
    },
  );
  return promptSummarySchema.array().parse(payload);
}

export async function createPrompt(
  input: PromptCreateInput,
  signal?: AbortSignal,
): Promise<PromptDetail> {
  const body = promptCreateInputSchema.parse(input);
  const payload = await requestJson("/api/prompts", {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });
  return promptDetailSchema.parse(payload);
}

export async function getPrompt(
  promptId: string,
  signal?: AbortSignal,
): Promise<PromptDetail> {
  const payload = await requestJson(`/api/prompts/${promptId}`, {
    method: "GET",
    signal,
  });
  return promptDetailSchema.parse(payload);
}

export async function updatePrompt(
  promptId: string,
  input: PromptUpdateInput,
  signal?: AbortSignal,
): Promise<PromptDetail> {
  const body = promptUpdateInputSchema.parse(input);
  const payload = await requestJson(`/api/prompts/${promptId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
    signal,
  });
  return promptDetailSchema.parse(payload);
}

export async function deletePrompt(
  promptId: string,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(buildUrl(`/api/prompts/${promptId}`), {
    method: "DELETE",
    signal,
  });

  if (!response.ok) {
    const payload = await parseJsonResponse(response);
    throw normalizeError(response, payload);
  }
}
