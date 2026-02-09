"use client";

import { useRouter } from "next/navigation";
import { ColumnsSection } from "@/features/reference-tables/components/detail/ColumnsSection";
import { ExportSection } from "@/features/reference-tables/components/detail/ExportSection";
import { ImportSection } from "@/features/reference-tables/components/detail/ImportSection";
import { MetadataSection } from "@/features/reference-tables/components/detail/MetadataSection";
import { QuerySection } from "@/features/reference-tables/components/detail/QuerySection";
import { RowEditorSheet } from "@/features/reference-tables/components/detail/RowEditorSheet";
import { RowMutationsSection } from "@/features/reference-tables/components/detail/RowMutationsSection";
import { useReferenceTableDetail } from "@/features/reference-tables/hooks/useReferenceTableDetail";
import { useReferenceTableMutations } from "@/features/reference-tables/hooks/useReferenceTableMutations";
import { useReferenceTableRowsQuery } from "@/features/reference-tables/hooks/useReferenceTableRowsQuery";
import { Button } from "@/shared/ui/button";

type ReferenceTableDetailPageProps = {
  tableId: string;
};

export function ReferenceTableDetailPage({
  tableId,
}: ReferenceTableDetailPageProps) {
  const router = useRouter();

  const {
    isMountedRef,
    table,
    isTableLoading,
    tableError,
    loadTable,
    refreshTableMetadata,
    isEditingMetadata,
    setIsEditingMetadata,
    metadataTitle,
    setMetadataTitle,
    metadataDescription,
    setMetadataDescription,
    metadataError,
    isSavingMetadata,
    saveMetadata,
    cancelMetadataEdit,
  } = useReferenceTableDetail({ tableId });

  const {
    filters,
    setFilters,
    sorts,
    setSorts,
    groupBy,
    setGroupBy,
    aggregates,
    setAggregates,
    pageSize,
    setPageSize,
    queryResult,
    queryError,
    isQueryLoading,
    buildQueryPayload,
    runQuery,
    resetQuery,
  } = useReferenceTableRowsQuery({
    table,
    isMountedRef,
  });

  const {
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
  } = useReferenceTableMutations({
    table,
    isMountedRef,
    currentQueryPage: queryResult?.page ?? 1,
    refreshTableMetadata,
    runQuery,
    buildQueryPayload,
  });

  const canStartImport = Boolean(importFile);

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
              void saveMetadata(event);
            }}
            onCancelMetadataEdit={cancelMetadataEdit}
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
              resetQuery();
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
              canStartImport={canStartImport}
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
