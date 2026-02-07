"use client";

import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { uploadAgentAttachments } from "@/lib/api/clients/agent.client";
import {
  batchMutateTableRows,
  exportTable,
  getTable,
  getTableImportJob,
  queryTableRows,
  startTableImport,
  updateTable,
} from "@/lib/api/clients/tables.client";
import type {
  ExportFormat,
  ImportJobSummary,
  QueriedRow,
  ReferenceTableDetail,
  RowsQueryResponse,
} from "@/lib/api/schemas/tables";
import { ColumnsSection } from "@/view/referenceTables/detail/ColumnsSection";
import type {
  AggregateDraft,
  FilterDraft,
  QueuedUpsert,
  SortDraft,
} from "@/view/referenceTables/detail/constants";
import { ExportSection } from "@/view/referenceTables/detail/ExportSection";
import { ImportSection } from "@/view/referenceTables/detail/ImportSection";
import { MetadataSection } from "@/view/referenceTables/detail/MetadataSection";
import { QuerySection } from "@/view/referenceTables/detail/QuerySection";
import { buildRowsQueryPayload } from "@/view/referenceTables/detail/queryPayload";
import { RowEditorSheet } from "@/view/referenceTables/detail/RowEditorSheet";
import { RowMutationsSection } from "@/view/referenceTables/detail/RowMutationsSection";
import {
  detectImportFormat,
  downloadBlob,
  extractRowValidationErrors,
  parseApiErrorMessage,
} from "@/view/referenceTables/utils";

type ReferenceTableDetailPageViewProps = {
  tableId: string;
};

const sleep = (ms: number) =>
  new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });

const newDraftId = (prefix: string) =>
  `${prefix}-${Date.now()}-${Math.floor(Math.random() * 10_000)}`;

export function ReferenceTableDetailPageView({
  tableId,
}: ReferenceTableDetailPageViewProps) {
  const router = useRouter();
  const isMountedRef = useRef(true);

  const [table, setTable] = useState<ReferenceTableDetail | null>(null);
  const [isTableLoading, setIsTableLoading] = useState(true);
  const [tableError, setTableError] = useState<string | null>(null);

  const [isEditingMetadata, setIsEditingMetadata] = useState(false);
  const [metadataTitle, setMetadataTitle] = useState("");
  const [metadataDescription, setMetadataDescription] = useState("");
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const [isSavingMetadata, setIsSavingMetadata] = useState(false);

  const [filters, setFilters] = useState<FilterDraft[]>([]);
  const [sorts, setSorts] = useState<SortDraft[]>([]);
  const [groupBy, setGroupBy] = useState<string[]>([]);
  const [aggregates, setAggregates] = useState<AggregateDraft[]>([]);
  const [pageSize, setPageSize] = useState(50);

  const [queryResult, setQueryResult] = useState<RowsQueryResponse | null>(
    null,
  );
  const [queryError, setQueryError] = useState<string | null>(null);
  const [isQueryLoading, setIsQueryLoading] = useState(false);

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

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const loadTable = useCallback(async () => {
    setIsTableLoading(true);
    setTableError(null);
    setQueryError(null);

    try {
      const detail = await getTable(tableId);
      const initialQuery = await queryTableRows(tableId, {
        filters: [],
        sorts: [],
        group_by: [],
        aggregates: [],
        page: 1,
        page_size: pageSize,
      });

      if (!isMountedRef.current) {
        return;
      }

      setTable(detail);
      setMetadataTitle(detail.title ?? "");
      setMetadataDescription(detail.description ?? "");
      setQueryResult(initialQuery);
    } catch (loadError) {
      if (!isMountedRef.current) {
        return;
      }

      setTableError(parseApiErrorMessage(loadError, "Failed to load table."));
    } finally {
      if (isMountedRef.current) {
        setIsTableLoading(false);
      }
    }
  }, [pageSize, tableId]);

  useEffect(() => {
    void loadTable();
  }, [loadTable]);

  const refreshTableMetadata = useCallback(async () => {
    const detail = await getTable(tableId);
    if (!isMountedRef.current) {
      return;
    }
    setTable(detail);
    setMetadataTitle(detail.title ?? "");
    setMetadataDescription(detail.description ?? "");
  }, [tableId]);

  const buildQueryPayload = useCallback(
    (page: number) =>
      buildRowsQueryPayload({
        table,
        filters,
        sorts,
        groupBy,
        aggregates,
        page,
        pageSize,
      }),
    [aggregates, filters, groupBy, pageSize, sorts, table],
  );

  const runQuery = useCallback(
    async (page = 1) => {
      if (!table) {
        return;
      }

      setIsQueryLoading(true);
      setQueryError(null);
      setBatchSuccess(null);

      try {
        const payload = buildQueryPayload(page);
        const result = await queryTableRows(table.id, payload);
        if (!isMountedRef.current) {
          return;
        }

        setQueryResult(result);
      } catch (queryLoadError) {
        if (!isMountedRef.current) {
          return;
        }

        setQueryError(
          parseApiErrorMessage(queryLoadError, "Failed to query rows."),
        );
      } finally {
        if (isMountedRef.current) {
          setIsQueryLoading(false);
        }
      }
    },
    [buildQueryPayload, table],
  );

  const queuedDeleteSet = useMemo(
    () => new Set(queuedDeleteRowIds),
    [queuedDeleteRowIds],
  );

  const handleSaveMetadata = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!table) {
      return;
    }

    const nextTitle = metadataTitle.trim();
    const nextDescription = metadataDescription.trim();

    const payload: {
      title?: string;
      description?: string;
    } = {};

    if (nextTitle && nextTitle !== (table.title ?? "")) {
      payload.title = nextTitle;
    }
    if (nextDescription && nextDescription !== (table.description ?? "")) {
      payload.description = nextDescription;
    }

    if (Object.keys(payload).length === 0) {
      setIsEditingMetadata(false);
      return;
    }

    setIsSavingMetadata(true);
    setMetadataError(null);
    try {
      const updated = await updateTable(table.id, payload);
      if (!isMountedRef.current) {
        return;
      }

      setTable(updated);
      setMetadataTitle(updated.title ?? "");
      setMetadataDescription(updated.description ?? "");
      setIsEditingMetadata(false);
    } catch (saveError) {
      if (!isMountedRef.current) {
        return;
      }

      setMetadataError(
        parseApiErrorMessage(saveError, "Failed to update table metadata."),
      );
    } finally {
      if (isMountedRef.current) {
        setIsSavingMetadata(false);
      }
    }
  };

  const openNewRowEditor = () => {
    setRowEditorRowId(null);
    setRowEditorJson("{}");
    setRowEditorError(null);
    setIsRowEditorOpen(true);
  };

  const openExistingRowEditor = (row: QueriedRow) => {
    setRowEditorRowId(row.id);
    setRowEditorJson(JSON.stringify(row.values_json, null, 2));
    setRowEditorError(null);
    setIsRowEditorOpen(true);
  };

  const saveRowEditor = () => {
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
  };

  const toggleQueuedDelete = (rowId: string) => {
    setQueuedDeleteRowIds((prev) =>
      prev.includes(rowId)
        ? prev.filter((item) => item !== rowId)
        : [...prev, rowId],
    );

    setQueuedUpserts((prev) => prev.filter((item) => item.row_id !== rowId));
    setBatchSuccess(null);
  };

  const clearQueue = () => {
    setQueuedUpserts([]);
    setQueuedDeleteRowIds([]);
    setBatchError(null);
    setBatchValidationErrors([]);
    setBatchSuccess(null);
  };

  const saveQueuedMutations = async () => {
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
      await runQuery(queryResult?.page ?? 1);
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
  };

  const pollImportJob = useCallback(
    async (
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
    [tableId],
  );

  const startImport = async () => {
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

      const finalPolled = await pollImportJob(started.id, started.status);
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
  };

  const runExport = async () => {
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
  };

  if (isTableLoading) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="rounded-2xl border border-marketing-border bg-marketing-surface px-6 py-4 text-sm text-marketing-text-secondary shadow-marketing-subtle">
          Loading table...
        </div>
      </div>
    );
  }

  if (tableError || !table) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="w-full max-w-lg rounded-2xl border border-marketing-border bg-marketing-surface p-6 shadow-marketing-subtle">
          <h2 className="text-lg font-semibold text-marketing-text-primary">
            Unable to load table
          </h2>
          <p className="mt-2 text-sm text-marketing-text-secondary">
            {tableError ?? "Table was not found."}
          </p>
          <div className="mt-4 flex gap-2">
            <Button type="button" onClick={() => void loadTable()}>
              Retry
            </Button>
            <Button
              type="button"
              variant="outline"
              className="border-marketing-border"
              onClick={() => router.push("/reference-tables")}
            >
              Back to tables
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-1 flex-col overflow-y-auto p-4 md:p-8">
        <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-5">
          <MetadataSection
            table={table}
            isEditingMetadata={isEditingMetadata}
            metadataTitle={metadataTitle}
            metadataDescription={metadataDescription}
            metadataError={metadataError}
            isSavingMetadata={isSavingMetadata}
            isExporting={isExporting}
            onBack={() => router.push("/reference-tables")}
            onToggleEditMetadata={() => setIsEditingMetadata((prev) => !prev)}
            onMetadataTitleChange={setMetadataTitle}
            onMetadataDescriptionChange={setMetadataDescription}
            onSaveMetadata={(event) => {
              void handleSaveMetadata(event);
            }}
            onCancelMetadataEdit={() => {
              setIsEditingMetadata(false);
              setMetadataTitle(table.title ?? "");
              setMetadataDescription(table.description ?? "");
              setMetadataError(null);
            }}
            onExport={() => {
              void runExport();
            }}
          />

          <ColumnsSection table={table} />

          <QuerySection
            table={table}
            filters={filters}
            sorts={sorts}
            groupBy={groupBy}
            aggregates={aggregates}
            pageSize={pageSize}
            queryResult={queryResult}
            queryError={queryError}
            isQueryLoading={isQueryLoading}
            queuedDeleteSet={queuedDeleteSet}
            setFilters={setFilters}
            setSorts={setSorts}
            setGroupBy={setGroupBy}
            setAggregates={setAggregates}
            setPageSize={setPageSize}
            onRunQuery={(page) => {
              void runQuery(page);
            }}
            onResetQuery={() => {
              setFilters([]);
              setSorts([]);
              setGroupBy([]);
              setAggregates([]);
              setQueryError(null);
              void runQuery(1);
            }}
            onOpenExistingRowEditor={openExistingRowEditor}
            onToggleQueuedDelete={toggleQueuedDelete}
          />

          <RowMutationsSection
            queuedUpserts={queuedUpserts}
            queuedDeleteRowIds={queuedDeleteRowIds}
            batchError={batchError}
            batchValidationErrors={batchValidationErrors}
            batchSuccess={batchSuccess}
            isSavingBatch={isSavingBatch}
            queryPage={queryResult?.page ?? 1}
            onOpenNewRowEditor={openNewRowEditor}
            onClearQueue={clearQueue}
            onSaveQueuedMutations={() => {
              void saveQueuedMutations();
            }}
            onRemoveQueuedUpsert={(clientId) => {
              setQueuedUpserts((prev) =>
                prev.filter((entry) => entry.client_id !== clientId),
              );
            }}
          />

          <div className="grid gap-5 lg:grid-cols-2">
            <ImportSection
              isImporting={isImporting}
              importError={importError}
              importJob={importJob}
              canStartImport={Boolean(importFile)}
              onFileChange={setImportFile}
              onStartImport={() => {
                void startImport();
              }}
            />

            <ExportSection
              exportFormat={exportFormat}
              includeHeader={includeHeader}
              includeCurrentQuery={includeCurrentQuery}
              isExporting={isExporting}
              exportError={exportError}
              onExportFormatChange={setExportFormat}
              onIncludeHeaderChange={setIncludeHeader}
              onIncludeCurrentQueryChange={setIncludeCurrentQuery}
              onRunExport={() => {
                void runExport();
              }}
            />
          </div>

          <div className="rounded-2xl border border-marketing-border bg-marketing-accent-soft px-4 py-3 text-sm text-marketing-text-secondary">
            Agent access available when table tools are enabled.
          </div>
        </div>
      </div>

      <RowEditorSheet
        open={isRowEditorOpen}
        rowId={rowEditorRowId}
        rowJson={rowEditorJson}
        rowError={rowEditorError}
        onOpenChange={setIsRowEditorOpen}
        onRowJsonChange={setRowEditorJson}
        onSave={saveRowEditor}
      />
    </>
  );
}
