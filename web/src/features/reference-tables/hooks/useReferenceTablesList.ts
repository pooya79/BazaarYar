import type { FormEvent } from "react";
import { useCallback, useEffect, useState } from "react";
import {
  downloadBlob,
  isAbortLikeError,
  parseApiErrorMessage,
} from "@/features/reference-tables/utils/tableUtils";
import {
  deleteTable,
  exportTable,
  listTables,
  updateTable,
} from "@/shared/api/clients/tables.client";
import type {
  ReferenceTableSummary,
  ReferenceTableUpdateInput,
} from "@/shared/api/schemas/tables";

export function useReferenceTablesList() {
  const [tables, setTables] = useState<ReferenceTableSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tableMenuOpenId, setTableMenuOpenId] = useState<string | null>(null);
  const [exportingTableId, setExportingTableId] = useState<string | null>(null);
  const [deletingTableId, setDeletingTableId] = useState<string | null>(null);

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

  const openEditSheet = useCallback((table: ReferenceTableSummary) => {
    setEditingTable(table);
    setEditTitle(table.title ?? "");
    setEditDescription(table.description ?? "");
    setEditError(null);
  }, []);

  const closeEditSheet = useCallback(() => {
    setEditingTable(null);
    setEditError(null);
  }, []);

  const submitEdit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
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
        closeEditSheet();
        return;
      }

      setIsSavingEdit(true);
      setEditError(null);
      try {
        await updateTable(editingTable.id, payload);
        await refreshTables();
        closeEditSheet();
      } catch (submitError) {
        setEditError(
          parseApiErrorMessage(submitError, "Failed to update table metadata."),
        );
      } finally {
        setIsSavingEdit(false);
      }
    },
    [closeEditSheet, editDescription, editTitle, editingTable, refreshTables],
  );

  const deleteTableWithConfirm = useCallback(
    async (table: ReferenceTableSummary) => {
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
    },
    [refreshTables],
  );

  const exportTableAsCsv = useCallback(async (table: ReferenceTableSummary) => {
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
  }, []);

  return {
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
  };
}
