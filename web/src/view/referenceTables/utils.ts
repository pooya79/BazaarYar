import type { ImportFormat, TableDataType } from "@/lib/api/schemas/tables";
import type { ApiError } from "@/lib/api/types";

export const TABLE_IDENTIFIER_PATTERN = /^[a-zA-Z_][a-zA-Z0-9_]{0,62}$/;

export const formatDateTime = (value: string): string => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
};

export const formatCellValue = (value: unknown): string => {
  if (value === null || value === undefined) {
    return "-";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
};

export const parseTypedInputValue = (
  raw: string,
  dataType: TableDataType,
): unknown => {
  const value = raw.trim();

  if (dataType === "text") {
    return value;
  }

  if (dataType === "integer") {
    const parsed = Number.parseInt(value, 10);
    if (Number.isNaN(parsed)) {
      throw new Error("Expected an integer value.");
    }
    return parsed;
  }

  if (dataType === "float") {
    const parsed = Number.parseFloat(value);
    if (Number.isNaN(parsed)) {
      throw new Error("Expected a numeric value.");
    }
    return parsed;
  }

  if (dataType === "boolean") {
    const normalized = value.toLowerCase();
    if (["true", "1", "yes", "y", "on"].includes(normalized)) {
      return true;
    }
    if (["false", "0", "no", "n", "off"].includes(normalized)) {
      return false;
    }
    throw new Error("Expected a boolean value (true/false). ");
  }

  if (dataType === "date" || dataType === "timestamp") {
    if (!value) {
      throw new Error("Expected an ISO date/time string.");
    }
    return value;
  }

  if (dataType === "json") {
    try {
      return JSON.parse(value);
    } catch {
      throw new Error("Expected valid JSON.");
    }
  }

  return value;
};

export const parseOptionalTypedValue = (
  raw: string,
  dataType: TableDataType,
): unknown => {
  if (!raw.trim()) {
    return null;
  }
  return parseTypedInputValue(raw, dataType);
};

export const parseApiErrorMessage = (
  error: unknown,
  fallback: string,
): string => {
  if (typeof error === "object" && error !== null && "message" in error) {
    const message = (error as ApiError).message;
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallback;
};

export const isAbortLikeError = (
  error: unknown,
  signal?: AbortSignal,
): boolean => {
  if (signal?.aborted) {
    return true;
  }

  if (error instanceof DOMException && error.name === "AbortError") {
    return true;
  }

  if (error instanceof Error) {
    if (error.name === "AbortError") {
      return true;
    }
    return error.message.toLowerCase().includes("aborted");
  }

  return false;
};

export const extractRowValidationErrors = (error: unknown): string[] => {
  if (!error || typeof error !== "object") {
    return [];
  }

  const details = (error as ApiError).details;
  if (!details || typeof details !== "object") {
    return [];
  }

  const detail = (details as { detail?: unknown }).detail;
  if (!detail || typeof detail !== "object") {
    return [];
  }

  const errors = (detail as { errors?: unknown }).errors;
  if (!Array.isArray(errors)) {
    return [];
  }

  return errors
    .map((entry) => {
      if (!entry || typeof entry !== "object") {
        return null;
      }

      const field =
        "field" in entry ? String((entry as { field?: unknown }).field) : "row";
      const reason =
        "error" in entry
          ? String((entry as { error?: unknown }).error)
          : "Invalid value";
      return `${field}: ${reason}`;
    })
    .filter((item): item is string => Boolean(item));
};

export const detectImportFormat = (
  filename: string,
): ImportFormat | undefined => {
  const lower = filename.toLowerCase();
  if (lower.endsWith(".csv")) {
    return "csv";
  }
  if (lower.endsWith(".json")) {
    return "json";
  }
  if (lower.endsWith(".xlsx")) {
    return "xlsx";
  }

  return undefined;
};

export const downloadBlob = (blob: Blob, filename: string): void => {
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
};
