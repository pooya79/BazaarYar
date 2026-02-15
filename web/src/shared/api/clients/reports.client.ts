import { buildUrl, normalizeError } from "../http";
import {
  type ReportCreateInput,
  type ReportDetail,
  type ReportSummary,
  type ReportUpdateInput,
  reportCreateInputSchema,
  reportDetailSchema,
  reportSummarySchema,
  reportUpdateInputSchema,
} from "../schemas/reports";

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

type ListReportsOptions = {
  q?: string;
  limit?: number;
  offset?: number;
  includeDisabled?: boolean;
  signal?: AbortSignal;
};

export async function listReports(
  options: ListReportsOptions = {},
): Promise<ReportSummary[]> {
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
  if (typeof options.includeDisabled === "boolean") {
    params.set("include_disabled", String(options.includeDisabled));
  }
  const query = params.toString();
  const payload = await requestJson(
    query ? `/api/reports?${query}` : "/api/reports",
    {
      method: "GET",
      signal: options.signal,
    },
  );
  return reportSummarySchema.array().parse(payload);
}

export async function createReport(
  input: ReportCreateInput,
  signal?: AbortSignal,
): Promise<ReportDetail> {
  const body = reportCreateInputSchema.parse(input);
  const payload = await requestJson("/api/reports", {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });
  return reportDetailSchema.parse(payload);
}

export async function getReport(
  reportId: string,
  signal?: AbortSignal,
): Promise<ReportDetail> {
  const payload = await requestJson(`/api/reports/${reportId}`, {
    method: "GET",
    signal,
  });
  return reportDetailSchema.parse(payload);
}

export async function updateReport(
  reportId: string,
  input: ReportUpdateInput,
  signal?: AbortSignal,
): Promise<ReportDetail> {
  const body = reportUpdateInputSchema.parse(input);
  const payload = await requestJson(`/api/reports/${reportId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
    signal,
  });
  return reportDetailSchema.parse(payload);
}

export async function deleteReport(
  reportId: string,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(buildUrl(`/api/reports/${reportId}`), {
    method: "DELETE",
    signal,
  });

  if (!response.ok) {
    const payload = await parseJsonResponse(response);
    throw normalizeError(response, payload);
  }
}
