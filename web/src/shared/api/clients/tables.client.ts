import { buildUrl, normalizeError } from "../http";
import {
  type ExportInput,
  exportInputSchema,
  type ImportFormat,
  type ImportJobSummary,
  type ImportStartInput,
  type InferColumnsResponse,
  importJobSummarySchema,
  importStartInputSchema,
  inferColumnsResponseSchema,
  type ReferenceTableCreateInput,
  type ReferenceTableDetail,
  type ReferenceTableSummary,
  type ReferenceTableUpdateInput,
  type RowsBatchInput,
  type RowsBatchResult,
  type RowsQueryInput,
  type RowsQueryResponse,
  referenceTableCreateInputSchema,
  referenceTableDetailSchema,
  referenceTableSummarySchema,
  referenceTableUpdateInputSchema,
  rowsBatchInputSchema,
  rowsBatchResultSchema,
  rowsQueryInputSchema,
  rowsQueryResponseSchema,
} from "../schemas/tables";

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

const extractFilename = (contentDisposition: string | null): string | null => {
  if (!contentDisposition) {
    return null;
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1].trim());
  }

  const basicMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  if (basicMatch?.[1]) {
    return basicMatch[1].trim();
  }

  return null;
};

type ListTablesOptions = {
  limit?: number;
  offset?: number;
  signal?: AbortSignal;
};

export async function listTables(
  options: ListTablesOptions = {},
): Promise<ReferenceTableSummary[]> {
  const params = new URLSearchParams();
  if (typeof options.limit === "number") {
    params.set("limit", String(options.limit));
  }
  if (typeof options.offset === "number") {
    params.set("offset", String(options.offset));
  }

  const query = params.toString();
  const payload = await requestJson(
    query ? `/api/tables?${query}` : "/api/tables",
    {
      method: "GET",
      signal: options.signal,
    },
  );

  return referenceTableSummarySchema.array().parse(payload);
}

export async function createTable(
  input: ReferenceTableCreateInput,
  signal?: AbortSignal,
): Promise<ReferenceTableDetail> {
  const body = referenceTableCreateInputSchema.parse(input);
  const payload = await requestJson("/api/tables", {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });

  return referenceTableDetailSchema.parse(payload);
}

export async function getTable(
  tableId: string,
  signal?: AbortSignal,
): Promise<ReferenceTableDetail> {
  const payload = await requestJson(`/api/tables/${tableId}`, {
    method: "GET",
    signal,
  });

  return referenceTableDetailSchema.parse(payload);
}

export async function updateTable(
  tableId: string,
  input: ReferenceTableUpdateInput,
  signal?: AbortSignal,
): Promise<ReferenceTableDetail> {
  const body = referenceTableUpdateInputSchema.parse(input);
  const payload = await requestJson(`/api/tables/${tableId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
    signal,
  });

  return referenceTableDetailSchema.parse(payload);
}

export async function deleteTable(
  tableId: string,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(buildUrl(`/api/tables/${tableId}`), {
    method: "DELETE",
    signal,
  });

  if (!response.ok) {
    const payload = await parseJsonResponse(response);
    throw normalizeError(response, payload);
  }
}

export async function queryTableRows(
  tableId: string,
  input: RowsQueryInput,
  signal?: AbortSignal,
): Promise<RowsQueryResponse> {
  const body = rowsQueryInputSchema.parse(input);
  const payload = await requestJson(`/api/tables/${tableId}/rows/query`, {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });

  return rowsQueryResponseSchema.parse(payload);
}

export async function batchMutateTableRows(
  tableId: string,
  input: RowsBatchInput,
  signal?: AbortSignal,
): Promise<RowsBatchResult> {
  const body = rowsBatchInputSchema.parse(input);
  const payload = await requestJson(`/api/tables/${tableId}/rows/batch`, {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });

  return rowsBatchResultSchema.parse(payload);
}

export async function startTableImport(
  tableId: string,
  input: ImportStartInput,
  signal?: AbortSignal,
): Promise<ImportJobSummary> {
  const body = importStartInputSchema.parse(input);
  const payload = await requestJson(`/api/tables/${tableId}/imports`, {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });

  return importJobSummarySchema.parse(payload);
}

type InferTableColumnsOptions = {
  sourceFormat?: ImportFormat;
  hasHeader?: boolean;
  delimiter?: string;
  signal?: AbortSignal;
};

export async function inferTableColumns(
  file: File,
  options: InferTableColumnsOptions = {},
): Promise<InferColumnsResponse> {
  const formData = new FormData();
  formData.set("file", file);
  if (options.sourceFormat) {
    formData.set("source_format", options.sourceFormat);
  }
  if (typeof options.hasHeader === "boolean") {
    formData.set("has_header", String(options.hasHeader));
  }
  if (options.delimiter) {
    formData.set("delimiter", options.delimiter);
  }

  const response = await fetch(buildUrl("/api/tables/infer-columns"), {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
    body: formData,
    signal: options.signal,
  });

  const payload = await parseJsonResponse(response);
  if (!response.ok) {
    throw normalizeError(response, payload);
  }

  return inferColumnsResponseSchema.parse(payload);
}

export async function getTableImportJob(
  tableId: string,
  jobId: string,
  signal?: AbortSignal,
): Promise<ImportJobSummary> {
  const payload = await requestJson(`/api/tables/${tableId}/imports/${jobId}`, {
    method: "GET",
    signal,
  });

  return importJobSummarySchema.parse(payload);
}

export type TableExportResult = {
  blob: Blob;
  filename: string;
  contentType: string;
};

export async function exportTable(
  tableId: string,
  input: ExportInput,
  signal?: AbortSignal,
): Promise<TableExportResult> {
  const body = exportInputSchema.parse(input);

  const response = await fetch(buildUrl(`/api/tables/${tableId}/export`), {
    method: "POST",
    headers: {
      Accept: "*/*",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    const payload = await parseJsonResponse(response);
    throw normalizeError(response, payload);
  }

  const blob = await response.blob();
  const filename =
    extractFilename(response.headers.get("Content-Disposition")) ??
    `${tableId}.${body.format}`;

  return {
    blob,
    filename,
    contentType:
      response.headers.get("Content-Type") ?? "application/octet-stream",
  };
}
