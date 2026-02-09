import type { MutableRefObject } from "react";
import { useCallback, useMemo, useState } from "react";
import type { QueuedUpsert } from "@/features/reference-tables/model/queryDrafts";
import {
  detectImportFormat,
  downloadBlob,
  extractRowValidationErrors,
  parseApiErrorMessage,
} from "@/features/reference-tables/utils/tableUtils";
import { uploadAgentAttachments } from "@/shared/api/clients/agent.client";
import {
  batchMutateTableRows,
  exportTable,
  getTableImportJob,
  startTableImport,
} from "@/shared/api/clients/tables.client";
import type {
  ExportFormat,
  ImportJobSummary,
  QueriedRow,
  ReferenceTableDetail,
  RowsQueryInput,
} from "@/shared/api/schemas/tables";

type UseReferenceTableMutationsParams = {
  table: ReferenceTableDetail | null;
  isMountedRef: MutableRefObject<boolean>;
  currentQueryPage: number;
  refreshTableMetadata: () => Promise<void>;
  runQuery: (page?: number) => Promise<void>;
  buildQueryPayload: (page: number) => RowsQueryInput;
};

const sleep = (ms: number) =>
  new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });

const newDraftId = (prefix: string) =>
  `${prefix}-${Date.now()}-${Math.floor(Math.random() * 10_000)}`;

export function useReferenceTableMutations({
  table,
  isMountedRef,
  currentQueryPage,
  refreshTableMetadata,
  runQuery,
  buildQueryPayload,
}: UseReferenceTableMutationsParams) {
  const [queuedUpserts, setQueuedUpserts] = useState<QueuedUpsert[]>([]);
  const [queuedDeleteRowIds, setQueuedDeleteRowIds] = useState<string[]>([]);
  const [batchError, setBatchError] = useState<string | null>(null);
  const [batchValidationErrors, setBatchValidationErrors] = useState<string[]>(
    [],
  );
  const [batchSuccess, setBatchSuccess] = useState<string | null>(null);
  const [isSavingBatch, setIsSavingBatch] = useState(false);

  const [isRowEditorOpen, setIsRowEditorOpen] = useState(false);
  const [rowEditorRowId, setRowEditorRowId] = useState<string | null>(null);
  const [rowEditorJson, setRowEditorJson] = useState("{}");
  const [rowEditorError, setRowEditorError] = useState<string | null>(null);

  const [importFile, setImportFile] = useState<File | null>(null);
  const [importJob, setImportJob] = useState<ImportJobSummary | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);

  const [exportFormat, setExportFormat] = useState<ExportFormat>("csv");
  const [includeHeader, setIncludeHeader] = useState(true);
  const [includeCurrentQuery, setIncludeCurrentQuery] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const queuedDeleteSet = useMemo(
    () => new Set(queuedDeleteRowIds),
    [queuedDeleteRowIds],
  );

  const openNewRowEditor = useCallback(() => {
    setRowEditorRowId(null);
    setRowEditorJson("{}");
    setRowEditorError(null);
    setIsRowEditorOpen(true);
  }, []);

  const openExistingRowEditor = useCallback((row: QueriedRow) => {
    setRowEditorRowId(row.id);
    setRowEditorJson(JSON.stringify(row.values_json, null, 2));
    setRowEditorError(null);
    setIsRowEditorOpen(true);
  }, []);

  const saveRowEditor = useCallback(() => {
    setRowEditorError(null);

    try {
      const parsed = JSON.parse(rowEditorJson);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("Row JSON must be an object.");
      }

      setQueuedUpserts((prev) => {
        const rowData: QueuedUpsert = {
          client_id: rowEditorRowId ?? newDraftId("upsert"),
          row_id: rowEditorRowId ?? undefined,
          values_json: parsed as Record<string, unknown>,
        };

        if (!rowEditorRowId) {
          return [...prev, rowData];
        }

        const existingIndex = prev.findIndex(
          (item) => item.row_id === rowEditorRowId,
        );
        if (existingIndex === -1) {
          return [...prev, rowData];
        }

        const next = [...prev];
        next[existingIndex] = rowData;
        return next;
      });

      if (rowEditorRowId) {
        setQueuedDeleteRowIds((prev) =>
          prev.filter((rowId) => rowId !== rowEditorRowId),
        );
      }

      setIsRowEditorOpen(false);
      setBatchSuccess(null);
    } catch (saveError) {
      setRowEditorError(
        parseApiErrorMessage(saveError, "Invalid JSON payload."),
      );
    }
  }, [rowEditorJson, rowEditorRowId]);

  const toggleQueuedDelete = useCallback((rowId: string) => {
    setQueuedDeleteRowIds((prev) =>
      prev.includes(rowId)
        ? prev.filter((item) => item !== rowId)
        : [...prev, rowId],
    );

    setQueuedUpserts((prev) => prev.filter((item) => item.row_id !== rowId));
    setBatchSuccess(null);
  }, []);

  const clearQueue = useCallback(() => {
    setQueuedUpserts([]);
    setQueuedDeleteRowIds([]);
    setBatchError(null);
    setBatchValidationErrors([]);
    setBatchSuccess(null);
  }, []);

  const saveQueuedMutations = useCallback(async () => {
    if (!table) {
      return;
    }

    if (queuedUpserts.length === 0 && queuedDeleteRowIds.length === 0) {
      setBatchError("Queue at least one row change before saving.");
      return;
    }

    setIsSavingBatch(true);
    setBatchError(null);
    setBatchValidationErrors([]);
    setBatchSuccess(null);

    try {
      const result = await batchMutateTableRows(table.id, {
        upserts: queuedUpserts.map((row) => ({
          row_id: row.row_id ?? null,
          values_json: row.values_json,
          source_actor: "user",
        })),
        delete_row_ids: queuedDeleteRowIds,
      });

      if (!isMountedRef.current) {
        return;
      }

      setQueuedUpserts([]);
      setQueuedDeleteRowIds([]);
      setBatchSuccess(
        `Saved changes. Inserted ${result.inserted}, updated ${result.updated}, deleted ${result.deleted}.`,
      );

      await refreshTableMetadata();
      await runQuery(currentQueryPage);
    } catch (saveError) {
      if (!isMountedRef.current) {
        return;
      }

      setBatchError(
        parseApiErrorMessage(saveError, "Failed to save row mutations."),
      );
      setBatchValidationErrors(extractRowValidationErrors(saveError));
    } finally {
      if (isMountedRef.current) {
        setIsSavingBatch(false);
      }
    }
  }, [
    currentQueryPage,
    isMountedRef,
    queuedDeleteRowIds,
    queuedUpserts,
    refreshTableMetadata,
    runQuery,
    table,
  ]);

  const pollImportJob = useCallback(
    async (
      tableId: string,
      jobId: string,
      initialStatus: ImportJobSummary["status"],
    ): Promise<ImportJobSummary | null> => {
      let status = initialStatus;
      let latest: ImportJobSummary | null = null;

      for (let attempt = 0; attempt < 60; attempt += 1) {
        if (status === "completed" || status === "failed") {
          return latest;
        }

        await sleep(1500);
        if (!isMountedRef.current) {
          return latest;
        }

        latest = await getTableImportJob(tableId, jobId);
        status = latest.status;
        setImportJob(latest);
      }

      return latest;
    },
    [isMountedRef],
  );

  const startImport = useCallback(async () => {
    if (!table) {
      return;
    }
    if (!importFile) {
      setImportError("Select a file to import.");
      return;
    }

    setIsImporting(true);
    setImportError(null);
    setBatchSuccess(null);

    try {
      const uploaded = await uploadAgentAttachments([importFile]);
      if (uploaded.length === 0) {
        throw new Error("Failed to upload the import file.");
      }

      const started = await startTableImport(table.id, {
        attachment_id: uploaded[0].id,
        source_format: detectImportFormat(importFile.name),
        has_header: true,
        column_overrides: {},
      });
      setImportJob(started);

      const finalPolled = await pollImportJob(
        table.id,
        started.id,
        started.status,
      );
      const finalJob = finalPolled ?? started;

      if (finalJob.status === "failed") {
        setImportError("Import failed. Review import errors below.");
      }

      await refreshTableMetadata();
      await runQuery(1);
    } catch (importStartError) {
      setImportError(
        parseApiErrorMessage(importStartError, "Failed to import file."),
      );
    } finally {
      if (isMountedRef.current) {
        setIsImporting(false);
      }
    }
  }, [
    importFile,
    isMountedRef,
    pollImportJob,
    refreshTableMetadata,
    runQuery,
    table,
  ]);

  const runExport = useCallback(async () => {
    if (!table) {
      return;
    }

    setIsExporting(true);
    setExportError(null);

    try {
      const payload = {
        format: exportFormat,
        include_header: includeHeader,
        query: includeCurrentQuery ? buildQueryPayload(1) : undefined,
      };

      const exported = await exportTable(table.id, payload);
      downloadBlob(exported.blob, exported.filename);
    } catch (exportLoadError) {
      setExportError(
        parseApiErrorMessage(exportLoadError, "Failed to export table."),
      );
    } finally {
      if (isMountedRef.current) {
        setIsExporting(false);
      }
    }
  }, [
    buildQueryPayload,
    exportFormat,
    includeCurrentQuery,
    includeHeader,
    isMountedRef,
    table,
  ]);

  return {
    queuedUpserts,
    queuedDeleteRowIds,
    queuedDeleteSet,
    batchError,
    batchValidationErrors,
    batchSuccess,
    isSavingBatch,
    isRowEditorOpen,
    setIsRowEditorOpen,
    rowEditorRowId,
    rowEditorJson,
    setRowEditorJson,
    rowEditorError,
    openNewRowEditor,
    openExistingRowEditor,
    saveRowEditor,
    toggleQueuedDelete,
    clearQueue,
    saveQueuedMutations,
    setQueuedUpserts,
    importFile,
    setImportFile,
    importJob,
    importError,
    isImporting,
    startImport,
    exportFormat,
    setExportFormat,
    includeHeader,
    setIncludeHeader,
    includeCurrentQuery,
    setIncludeCurrentQuery,
    isExporting,
    exportError,
    runExport,
  };
}
