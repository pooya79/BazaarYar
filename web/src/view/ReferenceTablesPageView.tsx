"use client";

import { Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import {
  createTable,
  deleteTable,
  exportTable,
  listTables,
  updateTable,
} from "@/lib/api/clients/tables.client";
import type {
  ReferenceTableCreateInput,
  ReferenceTableSummary,
  ReferenceTableUpdateInput,
  TableDataType,
} from "@/lib/api/schemas/tables";
import { ReferenceTablesView } from "@/view/ReferenceTablesView";
import {
  downloadBlob,
  parseApiErrorMessage,
  parseOptionalTypedValue,
  TABLE_IDENTIFIER_PATTERN,
} from "@/view/referenceTables/utils";

type ColumnDraft = {
  id: string;
  name: string;
  data_type: TableDataType;
  nullable: boolean;
  default_value: string;
  description: string;
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

export function ReferenceTablesPageView() {
  const router = useRouter();

  const [tables, setTables] = useState<ReferenceTableSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tableMenuOpenId, setTableMenuOpenId] = useState<string | null>(null);
  const [exportingTableId, setExportingTableId] = useState<string | null>(null);
  const [deletingTableId, setDeletingTableId] = useState<string | null>(null);

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isSubmittingCreate, setIsSubmittingCreate] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createName, setCreateName] = useState("");
  const [createTitle, setCreateTitle] = useState("");
  const [createDescription, setCreateDescription] = useState("");
  const [createColumns, setCreateColumns] = useState<ColumnDraft[]>([
    createEmptyColumnDraft("column-1"),
  ]);

  const [editingTable, setEditingTable] =
    useState<ReferenceTableSummary | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const columnCounter = useRef(1);

  const nextColumnId = () => {
    columnCounter.current += 1;
    return `column-${columnCounter.current}`;
  };

  const refreshTables = useCallback(async (signal?: AbortSignal) => {
    setIsLoading(true);
    setError(null);
    try {
      const nextTables = await listTables({ signal });
      setTables(nextTables);
    } catch (loadError) {
      setError(parseApiErrorMessage(loadError, "Failed to load tables."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void refreshTables(controller.signal);
    return () => controller.abort();
  }, [refreshTables]);

  const resetCreateForm = () => {
    setCreateName("");
    setCreateTitle("");
    setCreateDescription("");
    setCreateColumns([createEmptyColumnDraft(nextColumnId())]);
    setCreateError(null);
  };

  const openCreateSheet = () => {
    resetCreateForm();
    setIsCreateOpen(true);
  };

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

    let payload: ReferenceTableCreateInput;
    try {
      payload = {
        name: normalizedName,
        title: createTitle.trim() ? createTitle.trim() : null,
        description: createDescription.trim() ? createDescription.trim() : null,
        columns: createColumns.map((column, index) => {
          const normalizedColumnName = column.name.trim();
          if (!TABLE_IDENTIFIER_PATTERN.test(normalizedColumnName)) {
            throw new Error(
              `Column ${index + 1} name must match ^[a-zA-Z_][a-zA-Z0-9_]{0,62}$.`,
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
      await refreshTables();
      setIsCreateOpen(false);
      router.push(`/reference-tables/${created.id}`);
    } catch (submitError) {
      setCreateError(
        parseApiErrorMessage(submitError, "Failed to create table."),
      );
    } finally {
      setIsSubmittingCreate(false);
    }
  };

  const openEditSheet = (table: ReferenceTableSummary) => {
    setEditingTable(table);
    setEditTitle(table.title ?? "");
    setEditDescription(table.description ?? "");
    setEditError(null);
  };

  const handleEditSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editingTable) {
      return;
    }

    const nextTitle = editTitle.trim();
    const nextDescription = editDescription.trim();

    const payload: ReferenceTableUpdateInput = {};
    if (nextTitle && nextTitle !== (editingTable.title ?? "")) {
      payload.title = nextTitle;
    }
    if (
      nextDescription &&
      nextDescription !== (editingTable.description ?? "")
    ) {
      payload.description = nextDescription;
    }

    if (Object.keys(payload).length === 0) {
      setEditingTable(null);
      return;
    }

    setIsSavingEdit(true);
    setEditError(null);
    try {
      await updateTable(editingTable.id, payload);
      await refreshTables();
      setEditingTable(null);
    } catch (submitError) {
      setEditError(
        parseApiErrorMessage(submitError, "Failed to update table metadata."),
      );
    } finally {
      setIsSavingEdit(false);
    }
  };

  const handleDeleteTable = async (table: ReferenceTableSummary) => {
    const confirmed = window.confirm(
      `Delete table "${table.title?.trim() || table.name}"? This cannot be undone.`,
    );

    if (!confirmed) {
      return;
    }

    setDeletingTableId(table.id);
    setTableMenuOpenId(null);
    try {
      await deleteTable(table.id);
      await refreshTables();
    } catch (deleteError) {
      window.alert(
        parseApiErrorMessage(deleteError, "Failed to delete table."),
      );
    } finally {
      setDeletingTableId(null);
    }
  };

  const handleExportTable = async (table: ReferenceTableSummary) => {
    setExportingTableId(table.id);
    setTableMenuOpenId(null);
    try {
      const exported = await exportTable(table.id, {
        format: "csv",
        include_header: true,
      });
      downloadBlob(exported.blob, exported.filename);
    } catch (exportError) {
      window.alert(
        parseApiErrorMessage(exportError, "Failed to export table."),
      );
    } finally {
      setExportingTableId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="rounded-2xl border border-marketing-border bg-marketing-surface px-6 py-4 text-sm text-marketing-text-secondary shadow-marketing-subtle">
          Loading reference tables...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="w-full max-w-lg rounded-2xl border border-marketing-border bg-marketing-surface p-6 shadow-marketing-subtle">
          <h2 className="text-lg font-semibold text-marketing-text-primary">
            Unable to load reference tables
          </h2>
          <p className="mt-2 text-sm text-marketing-text-secondary">{error}</p>
          <Button
            type="button"
            className="mt-4"
            onClick={() => {
              void refreshTables();
            }}
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <>
      <ReferenceTablesView
        tables={tables}
        tableMenuOpenId={tableMenuOpenId}
        exportingTableId={exportingTableId}
        deletingTableId={deletingTableId}
        onTableMenuOpenChange={setTableMenuOpenId}
        onCreateTable={openCreateSheet}
        onOpenTable={(tableId) => router.push(`/reference-tables/${tableId}`)}
        onEditTable={openEditSheet}
        onDeleteTable={(table) => {
          void handleDeleteTable(table);
        }}
        onExportTable={(table) => {
          void handleExportTable(table);
        }}
      />

      <Sheet open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <SheetContent
          side="right"
          className="w-full max-w-2xl overflow-y-auto border-marketing-border bg-marketing-surface p-0 sm:max-w-2xl"
        >
          <SheetHeader className="border-b border-marketing-border">
            <SheetTitle className="text-marketing-text-primary">
              Create table
            </SheetTitle>
            <SheetDescription className="text-marketing-text-secondary">
              Define metadata and columns for your reference table.
            </SheetDescription>
          </SheetHeader>

          <form onSubmit={handleCreateSubmit} className="space-y-5 p-4">
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

            <div className="space-y-2">
              <label className={labelClass} htmlFor="create-table-description">
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
                          <SelectContent>
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

            <SheetFooter className="border-t border-marketing-border px-0 pb-0">
              <Button
                type="button"
                variant="outline"
                className="border-marketing-border"
                onClick={() => setIsCreateOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isSubmittingCreate}
                className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
              >
                {isSubmittingCreate ? "Creating..." : "Create table"}
              </Button>
            </SheetFooter>
          </form>
        </SheetContent>
      </Sheet>

      <Sheet
        open={Boolean(editingTable)}
        onOpenChange={(open) => {
          if (!open) {
            setEditingTable(null);
          }
        }}
      >
        <SheetContent
          side="right"
          className="w-full max-w-xl border-marketing-border bg-marketing-surface p-0 sm:max-w-xl"
        >
          <SheetHeader className="border-b border-marketing-border">
            <SheetTitle className="text-marketing-text-primary">
              Edit table metadata
            </SheetTitle>
            <SheetDescription className="text-marketing-text-secondary">
              Update title and description for this table.
            </SheetDescription>
          </SheetHeader>

          <form onSubmit={handleEditSubmit} className="space-y-4 p-4">
            <div className="space-y-2">
              <label className={labelClass} htmlFor="edit-table-title">
                Title
              </label>
              <input
                id="edit-table-title"
                className={fieldClass}
                value={editTitle}
                onChange={(event) => setEditTitle(event.target.value)}
                placeholder="Campaign Metrics"
              />
            </div>

            <div className="space-y-2">
              <label className={labelClass} htmlFor="edit-table-description">
                Description
              </label>
              <Textarea
                id="edit-table-description"
                className="min-h-24 border-marketing-border text-marketing-text-primary"
                value={editDescription}
                onChange={(event) => setEditDescription(event.target.value)}
                placeholder="Describe how this table should be used."
              />
            </div>

            {editError && (
              <div className="rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
                {editError}
              </div>
            )}

            <SheetFooter className="border-t border-marketing-border px-0 pb-0">
              <Button
                type="button"
                variant="outline"
                className="border-marketing-border"
                onClick={() => setEditingTable(null)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isSavingEdit}
                className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
              >
                {isSavingEdit ? "Saving..." : "Save metadata"}
              </Button>
            </SheetFooter>
          </form>
        </SheetContent>
      </Sheet>
    </>
  );
}
