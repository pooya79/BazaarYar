"use client";

import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
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
  deleteTable,
  exportTable,
  listTables,
  updateTable,
} from "@/lib/api/clients/tables.client";
import type {
  ReferenceTableSummary,
  ReferenceTableUpdateInput,
} from "@/lib/api/schemas/tables";
import { ReferenceTablesView } from "@/view/ReferenceTablesView";
import { CreateTableModal } from "@/view/referenceTables/CreateTableModal";
import {
  downloadBlob,
  isAbortLikeError,
  parseApiErrorMessage,
} from "@/view/referenceTables/utils";

const fieldClass =
  "h-10 w-full rounded-lg border border-marketing-border bg-marketing-surface px-3 text-sm text-marketing-text-primary outline-none transition-colors focus:border-marketing-primary";

const labelClass =
  "text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted";

export function ReferenceTablesPageView() {
  const router = useRouter();

  const [tables, setTables] = useState<ReferenceTableSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tableMenuOpenId, setTableMenuOpenId] = useState<string | null>(null);
  const [exportingTableId, setExportingTableId] = useState<string | null>(null);
  const [deletingTableId, setDeletingTableId] = useState<string | null>(null);

  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const [editingTable, setEditingTable] =
    useState<ReferenceTableSummary | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const refreshTables = useCallback(async (signal?: AbortSignal) => {
    setIsLoading(true);
    setError(null);
    try {
      const nextTables = await listTables({ signal });
      setTables(nextTables);
    } catch (loadError) {
      if (isAbortLikeError(loadError, signal)) {
        return;
      }
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

  const handleTableCreated = async (tableId: string) => {
    await refreshTables();
    router.push(`/reference-tables/${tableId}`);
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
        onCreateTable={() => setIsCreateOpen(true)}
        onOpenTable={(tableId) => router.push(`/reference-tables/${tableId}`)}
        onEditTable={openEditSheet}
        onDeleteTable={(table) => {
          void handleDeleteTable(table);
        }}
        onExportTable={(table) => {
          void handleExportTable(table);
        }}
      />

      <CreateTableModal
        open={isCreateOpen}
        onOpenChange={setIsCreateOpen}
        onCreated={handleTableCreated}
      />

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
