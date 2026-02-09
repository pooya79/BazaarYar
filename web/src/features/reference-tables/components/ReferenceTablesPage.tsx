"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { CreateTableModal } from "@/features/reference-tables/components/CreateTableModal";
import { ReferenceTablesView } from "@/features/reference-tables/components/ReferenceTablesView";
import { useReferenceTablesList } from "@/features/reference-tables/hooks/useReferenceTablesList";
import { Button } from "@/shared/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/shared/ui/sheet";
import { Textarea } from "@/shared/ui/textarea";

const fieldClass =
  "h-10 w-full rounded-lg border border-marketing-border bg-marketing-surface px-3 text-sm text-marketing-text-primary outline-none transition-colors focus:border-marketing-primary";

const labelClass =
  "text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted";

export function ReferenceTablesPage() {
  const router = useRouter();
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const {
    tables,
    isLoading,
    error,
    refreshTables,
    tableMenuOpenId,
    setTableMenuOpenId,
    exportingTableId,
    deletingTableId,
    editingTable,
    editTitle,
    setEditTitle,
    editDescription,
    setEditDescription,
    isSavingEdit,
    editError,
    openEditSheet,
    closeEditSheet,
    submitEdit,
    deleteTableWithConfirm,
    exportTableAsCsv,
  } = useReferenceTablesList();

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
          void deleteTableWithConfirm(table);
        }}
        onExportTable={(table) => {
          void exportTableAsCsv(table);
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
            closeEditSheet();
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

          <form onSubmit={submitEdit} className="space-y-4 p-4">
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
                onClick={closeEditSheet}
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
