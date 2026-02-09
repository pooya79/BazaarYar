"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Loader2, Plus, Sparkles, Trash2, Upload, X } from "lucide-react";
import type { DragEvent, FormEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  COLUMN_IDENTIFIER_PATTERN,
  detectImportFormat,
  parseApiErrorMessage,
  parseOptionalTypedValue,
  TABLE_IDENTIFIER_PATTERN,
} from "@/features/reference-tables/utils/tableUtils";
import {
  createTable,
  inferTableColumns,
} from "@/shared/api/clients/tables.client";
import type {
  ReferenceTableColumnInput,
  TableDataType,
} from "@/shared/api/schemas/tables";
import { Button } from "@/shared/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/ui/select";
import { Textarea } from "@/shared/ui/textarea";

type ColumnDraft = {
  id: string;
  name: string;
  data_type: TableDataType;
  nullable: boolean;
  default_value: string;
  description: string;
};

type CreateTableModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (tableId: string) => void | Promise<void>;
};

const dataTypeOptions: Array<{ value: TableDataType; label: string }> = [
  { value: "text", label: "Text" },
  { value: "integer", label: "Integer" },
  { value: "float", label: "Float" },
  { value: "boolean", label: "Boolean" },
  { value: "date", label: "Date" },
  { value: "timestamp", label: "Timestamp" },
  { value: "json", label: "JSON" },
];

const fieldClass =
  "h-10 w-full rounded-lg border border-marketing-border bg-marketing-surface px-3 text-sm text-marketing-text-primary outline-none transition-colors focus:border-marketing-primary";

const labelClass =
  "text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted";

const createEmptyColumnDraft = (id: string): ColumnDraft => ({
  id,
  name: "",
  data_type: "text",
  nullable: true,
  default_value: "",
  description: "",
});

const toDefaultValueInput = (value: unknown): string => {
  if (value === null || value === undefined) {
    return "";
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

const normalizeIdentifier = (value: string): string => {
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }

  const normalized = trimmed
    .replace(/[^a-zA-Z0-9_]+/g, "_")
    .replace(/^_+|_+$/g, "");
  if (!normalized) {
    return "";
  }

  const prefixed = /^[a-zA-Z_]/.test(normalized)
    ? normalized
    : `table_${normalized}`;

  return prefixed.slice(0, 63);
};

const toTitleCase = (value: string): string => {
  const words = value
    .replace(/[_-]+/g, " ")
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  if (words.length === 0) {
    return "";
  }

  return words
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

const mapInferredColumnsToDrafts = (
  columns: ReferenceTableColumnInput[],
): ColumnDraft[] =>
  columns.map((column, index) => ({
    id: `column-${index + 1}`,
    name: column.name,
    data_type: column.data_type,
    nullable: column.nullable,
    default_value: toDefaultValueInput(column.default_value),
    description: column.description ?? "",
  }));

export function CreateTableModal({
  open,
  onOpenChange,
  onCreated,
}: CreateTableModalProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const columnCounter = useRef(1);

  const [isSubmittingCreate, setIsSubmittingCreate] = useState(false);
  const [isInferringColumns, setIsInferringColumns] = useState(false);
  const [isDropZoneActive, setIsDropZoneActive] = useState(false);

  const [createError, setCreateError] = useState<string | null>(null);
  const [inferError, setInferError] = useState<string | null>(null);
  const [inferSuccess, setInferSuccess] = useState<string | null>(null);

  const [createName, setCreateName] = useState("");
  const [createTitle, setCreateTitle] = useState("");
  const [createDescription, setCreateDescription] = useState("");
  const [createColumns, setCreateColumns] = useState<ColumnDraft[]>([
    createEmptyColumnDraft("column-1"),
  ]);

  const nextColumnId = () => {
    columnCounter.current += 1;
    return `column-${columnCounter.current}`;
  };

  const resetForm = useCallback(() => {
    columnCounter.current = 1;
    setCreateName("");
    setCreateTitle("");
    setCreateDescription("");
    setCreateColumns([createEmptyColumnDraft("column-1")]);
    setCreateError(null);
    setInferError(null);
    setInferSuccess(null);
    setIsDropZoneActive(false);
  }, []);

  useEffect(() => {
    if (open) {
      resetForm();
    }
  }, [open, resetForm]);

  const applyInferredSchema = useCallback(
    (
      inferred: {
        dataset_name_suggestion: string;
        source_format: string;
        row_count: number;
        columns: ReferenceTableColumnInput[];
      },
      filename: string,
    ) => {
      const nextColumns = mapInferredColumnsToDrafts(inferred.columns);
      if (nextColumns.length > 0) {
        columnCounter.current = nextColumns.length;
        setCreateColumns(nextColumns);
      }

      const suggestedName = normalizeIdentifier(
        inferred.dataset_name_suggestion,
      );
      if (suggestedName) {
        setCreateName(suggestedName);
      }

      const suggestedTitle = toTitleCase(inferred.dataset_name_suggestion);
      if (suggestedTitle) {
        setCreateTitle(suggestedTitle);
      }

      setInferSuccess(
        `Inferred ${inferred.columns.length} columns from ${inferred.row_count} rows (${inferred.source_format.toUpperCase()}) in ${filename}.`,
      );
      setCreateError(null);
    },
    [],
  );

  const handleInferFromFile = useCallback(
    async (file: File | null) => {
      if (!file) {
        return;
      }

      setInferError(null);
      setInferSuccess(null);
      setIsInferringColumns(true);

      try {
        const inferred = await inferTableColumns(file, {
          sourceFormat: detectImportFormat(file.name),
          hasHeader: true,
        });
        applyInferredSchema(inferred, file.name);
      } catch (error) {
        setInferError(
          parseApiErrorMessage(error, "Failed to infer columns from file."),
        );
      } finally {
        setIsInferringColumns(false);
      }
    },
    [applyInferredSchema],
  );

  const handleCreateSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreateError(null);

    const normalizedName = createName.trim();
    if (!TABLE_IDENTIFIER_PATTERN.test(normalizedName)) {
      setCreateError("Table name must match ^[a-zA-Z_][a-zA-Z0-9_]{0,62}$.");
      return;
    }

    if (createColumns.length === 0) {
      setCreateError("Add at least one column.");
      return;
    }

    let payload: {
      name: string;
      title: string | null;
      description: string | null;
      columns: ReferenceTableColumnInput[];
    };

    try {
      payload = {
        name: normalizedName,
        title: createTitle.trim() ? createTitle.trim() : null,
        description: createDescription.trim() ? createDescription.trim() : null,
        columns: createColumns.map((column, index) => {
          const normalizedColumnName = column.name.trim();
          if (!COLUMN_IDENTIFIER_PATTERN.test(normalizedColumnName)) {
            throw new Error(
              `Column ${index + 1} name must be 1-63 characters.`,
            );
          }

          return {
            name: normalizedColumnName,
            data_type: column.data_type,
            nullable: column.nullable,
            default_value: parseOptionalTypedValue(
              column.default_value,
              column.data_type,
            ),
            description: column.description.trim()
              ? column.description.trim()
              : null,
          };
        }),
      };
    } catch (buildError) {
      setCreateError(
        parseApiErrorMessage(buildError, "Failed to validate table schema."),
      );
      return;
    }

    setIsSubmittingCreate(true);
    try {
      const created = await createTable(payload);
      await onCreated(created.id);
      onOpenChange(false);
    } catch (submitError) {
      setCreateError(
        parseApiErrorMessage(submitError, "Failed to create table."),
      );
    } finally {
      setIsSubmittingCreate(false);
    }
  };

  const handleDrop = (event: DragEvent<HTMLElement>) => {
    event.preventDefault();
    setIsDropZoneActive(false);
    const file = event.dataTransfer.files?.[0] ?? null;
    void handleInferFromFile(file);
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[140] bg-black/60 backdrop-blur-[1px]" />
        <Dialog.Content className="fixed top-1/2 left-1/2 z-[150] flex h-[min(92vh,58rem)] w-[min(96vw,58rem)] -translate-x-1/2 -translate-y-1/2 flex-col rounded-2xl border border-marketing-border bg-marketing-surface shadow-marketing-glow">
          <div className="flex items-start justify-between border-b border-marketing-border p-5">
            <div>
              <Dialog.Title className="text-lg font-semibold text-marketing-text-primary">
                Create table
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-marketing-text-secondary">
                Define table metadata manually or infer columns from a file.
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="inline-flex size-9 items-center justify-center rounded-lg border border-marketing-border bg-marketing-surface text-marketing-text-secondary transition-colors hover:text-marketing-text-primary"
                aria-label="Close"
              >
                <X className="size-4" aria-hidden="true" />
              </button>
            </Dialog.Close>
          </div>

          <form
            onSubmit={handleCreateSubmit}
            className="flex min-h-0 flex-1 flex-col"
          >
            <div className="space-y-5 overflow-y-auto p-5">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <label className={labelClass} htmlFor="create-table-name">
                    Name
                  </label>
                  <input
                    id="create-table-name"
                    className={fieldClass}
                    value={createName}
                    onChange={(event) => setCreateName(event.target.value)}
                    placeholder="campaign_metrics"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <label className={labelClass} htmlFor="create-table-title">
                    Title
                  </label>
                  <input
                    id="create-table-title"
                    className={fieldClass}
                    value={createTitle}
                    onChange={(event) => setCreateTitle(event.target.value)}
                    placeholder="Campaign Metrics"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label
                  className={labelClass}
                  htmlFor="create-table-description"
                >
                  Description
                </label>
                <Textarea
                  id="create-table-description"
                  className="min-h-20 border-marketing-border text-marketing-text-primary"
                  value={createDescription}
                  onChange={(event) => setCreateDescription(event.target.value)}
                  placeholder="Daily campaign-level KPIs and budget outcomes."
                />
              </div>

              <label
                htmlFor="infer-columns-file-input"
                className={`block cursor-pointer rounded-2xl border border-dashed p-5 transition-colors ${
                  isDropZoneActive
                    ? "border-marketing-primary bg-marketing-primary-soft"
                    : "border-marketing-border bg-marketing-accent-soft"
                }`}
                onDragOver={(event) => {
                  event.preventDefault();
                  setIsDropZoneActive(true);
                }}
                onDragLeave={() => {
                  setIsDropZoneActive(false);
                }}
                onDrop={handleDrop}
              >
                <div className="mx-auto flex size-11 items-center justify-center rounded-full bg-marketing-surface text-marketing-primary">
                  {isInferringColumns ? (
                    <Loader2
                      className="size-5 animate-spin"
                      aria-hidden="true"
                    />
                  ) : (
                    <Upload className="size-5" aria-hidden="true" />
                  )}
                </div>
                <h3 className="mt-3 text-center text-sm font-semibold uppercase tracking-[1px] text-marketing-text-muted">
                  Infer columns using a file
                </h3>
                <p className="mt-1 text-center text-sm text-marketing-text-secondary">
                  Drop a CSV, JSON, or XLSX file here. We will infer schema and
                  fill the table form automatically.
                </p>
                <div className="mt-4 flex justify-center">
                  <span className="inline-flex items-center gap-2 rounded-lg border border-marketing-border bg-marketing-surface px-4 py-2 text-sm font-medium text-marketing-text-primary">
                    <Sparkles className="size-4" aria-hidden="true" />
                    Choose file
                  </span>
                  <input
                    ref={fileInputRef}
                    id="infer-columns-file-input"
                    type="file"
                    accept=".csv,.json,.xlsx"
                    className="hidden"
                    disabled={isInferringColumns}
                    onChange={(event) => {
                      const file = event.target.files?.[0] ?? null;
                      void handleInferFromFile(file);
                      event.currentTarget.value = "";
                    }}
                  />
                </div>
                {inferError && (
                  <div className="mt-4 rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
                    {inferError}
                  </div>
                )}
                {inferSuccess && (
                  <div className="mt-4 rounded-lg border border-marketing-border bg-marketing-surface px-3 py-2 text-sm text-marketing-text-secondary">
                    {inferSuccess}
                  </div>
                )}
              </label>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold uppercase tracking-[1px] text-marketing-text-muted">
                    Columns
                  </h3>
                  <Button
                    type="button"
                    variant="outline"
                    className="border-marketing-border"
                    onClick={() => {
                      setCreateColumns((prev) => [
                        ...prev,
                        createEmptyColumnDraft(nextColumnId()),
                      ]);
                    }}
                  >
                    <Plus className="size-4" aria-hidden="true" />
                    Add column
                  </Button>
                </div>

                <div className="space-y-3">
                  {createColumns.map((column, index) => (
                    <div
                      key={column.id}
                      className="space-y-3 rounded-xl border border-marketing-border bg-marketing-accent-soft p-3"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
                          Column {index + 1}
                        </p>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-sm"
                          className="text-marketing-danger hover:bg-marketing-danger-soft"
                          onClick={() => {
                            setCreateColumns((prev) =>
                              prev.length <= 1
                                ? prev
                                : prev.filter((item) => item.id !== column.id),
                            );
                          }}
                          disabled={createColumns.length <= 1}
                          aria-label="Remove column"
                        >
                          <Trash2 className="size-4" aria-hidden="true" />
                        </Button>
                      </div>

                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="space-y-2">
                          <label
                            className={labelClass}
                            htmlFor={`column-name-${column.id}`}
                          >
                            Column name
                          </label>
                          <input
                            id={`column-name-${column.id}`}
                            className={fieldClass}
                            value={column.name}
                            onChange={(event) => {
                              const nextValue = event.target.value;
                              setCreateColumns((prev) =>
                                prev.map((item) =>
                                  item.id === column.id
                                    ? { ...item, name: nextValue }
                                    : item,
                                ),
                              );
                            }}
                            placeholder="impressions"
                            required
                          />
                        </div>

                        <div className="space-y-2">
                          <p className={labelClass}>Data type</p>
                          <Select
                            value={column.data_type}
                            onValueChange={(value) => {
                              setCreateColumns((prev) =>
                                prev.map((item) =>
                                  item.id === column.id
                                    ? {
                                        ...item,
                                        data_type: value as TableDataType,
                                      }
                                    : item,
                                ),
                              );
                            }}
                          >
                            <SelectTrigger className="h-10 w-full border-marketing-border bg-marketing-surface text-marketing-text-primary">
                              <SelectValue placeholder="Select type" />
                            </SelectTrigger>
                            <SelectContent className="z-[170]">
                              {dataTypeOptions.map((option) => (
                                <SelectItem
                                  key={option.value}
                                  value={option.value}
                                >
                                  {option.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="space-y-2">
                          <label
                            className={labelClass}
                            htmlFor={`column-default-${column.id}`}
                          >
                            Default value
                          </label>
                          <input
                            id={`column-default-${column.id}`}
                            className={fieldClass}
                            value={column.default_value}
                            onChange={(event) => {
                              const nextValue = event.target.value;
                              setCreateColumns((prev) =>
                                prev.map((item) =>
                                  item.id === column.id
                                    ? { ...item, default_value: nextValue }
                                    : item,
                                ),
                              );
                            }}
                            placeholder="Optional"
                          />
                        </div>

                        <div className="flex items-center gap-2 pt-7">
                          <input
                            id={`column-nullable-${column.id}`}
                            type="checkbox"
                            checked={column.nullable}
                            onChange={(event) => {
                              const checked = event.target.checked;
                              setCreateColumns((prev) =>
                                prev.map((item) =>
                                  item.id === column.id
                                    ? { ...item, nullable: checked }
                                    : item,
                                ),
                              );
                            }}
                            className="size-4 rounded border-marketing-border"
                          />
                          <label
                            htmlFor={`column-nullable-${column.id}`}
                            className="text-sm text-marketing-text-secondary"
                          >
                            Nullable
                          </label>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <label
                          className={labelClass}
                          htmlFor={`column-description-${column.id}`}
                        >
                          Description
                        </label>
                        <input
                          id={`column-description-${column.id}`}
                          className={fieldClass}
                          value={column.description}
                          onChange={(event) => {
                            const nextValue = event.target.value;
                            setCreateColumns((prev) =>
                              prev.map((item) =>
                                item.id === column.id
                                  ? { ...item, description: nextValue }
                                  : item,
                              ),
                            );
                          }}
                          placeholder="Column intent"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {createError && (
                <div className="rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
                  {createError}
                </div>
              )}
            </div>

            <div className="mt-auto flex items-center justify-end gap-2 border-t border-marketing-border p-5">
              <Button
                type="button"
                variant="outline"
                className="border-marketing-border"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isSubmittingCreate || isInferringColumns}
                className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
              >
                {isSubmittingCreate ? "Creating..." : "Create table"}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
