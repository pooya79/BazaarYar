import { Button } from "@/components/ui/button";
import type {
  QueriedRow,
  ReferenceTableDetail,
  RowsQueryResponse,
} from "@/lib/api/schemas/tables";
import { formatCellValue, formatDateTime } from "@/view/referenceTables/utils";

type QueryResultsPanelProps = {
  table: ReferenceTableDetail;
  queryResult: RowsQueryResponse;
  canPageBack: boolean;
  canPageForward: boolean;
  queuedDeleteSet: Set<string>;
  onRunQuery: (page?: number) => void;
  onOpenExistingRowEditor: (row: QueriedRow) => void;
  onToggleQueuedDelete: (rowId: string) => void;
};

export function QueryResultsPanel({
  table,
  queryResult,
  canPageBack,
  canPageForward,
  queuedDeleteSet,
  onRunQuery,
  onOpenExistingRowEditor,
  onToggleQueuedDelete,
}: QueryResultsPanelProps) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-marketing-text-secondary">
        <span>
          Total rows: {queryResult.total_rows.toLocaleString()} | Page{" "}
          {queryResult.page}
        </span>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            className="h-8 border-marketing-border"
            onClick={() => {
              if (canPageBack) {
                onRunQuery(queryResult.page - 1);
              }
            }}
            disabled={!canPageBack}
          >
            Previous
          </Button>
          <Button
            type="button"
            variant="outline"
            className="h-8 border-marketing-border"
            onClick={() => {
              if (canPageForward) {
                onRunQuery(queryResult.page + 1);
              }
            }}
            disabled={!canPageForward}
          >
            Next
          </Button>
        </div>
      </div>

      {queryResult.rows.length === 0 ? (
        <div className="rounded-lg border border-dashed border-marketing-border bg-marketing-accent-soft px-3 py-6 text-center text-sm text-marketing-text-secondary">
          No rows returned for this query.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-marketing-border">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-marketing-accent-soft text-marketing-text-muted">
              <tr>
                <th className="px-2 py-2 font-semibold">Row ID</th>
                {table.columns.map((column) => (
                  <th key={column.id} className="px-2 py-2 font-semibold">
                    {column.name}
                  </th>
                ))}
                <th className="px-2 py-2 font-semibold">Version</th>
                <th className="px-2 py-2 font-semibold">Updated</th>
                <th className="px-2 py-2 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {queryResult.rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-t border-marketing-border/70"
                >
                  <td className="px-2 py-2 font-mono text-xs text-marketing-text-secondary">
                    {row.id}
                  </td>
                  {table.columns.map((column) => (
                    <td
                      key={`${row.id}-${column.id}`}
                      className="max-w-[220px] px-2 py-2 text-marketing-text-primary"
                    >
                      <span className="line-clamp-2">
                        {formatCellValue(row.values_json[column.name])}
                      </span>
                    </td>
                  ))}
                  <td className="px-2 py-2 text-marketing-text-secondary">
                    {row.version}
                  </td>
                  <td className="px-2 py-2 text-marketing-text-secondary">
                    {formatDateTime(row.updated_at)}
                  </td>
                  <td className="px-2 py-2">
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-7 border-marketing-border"
                        onClick={() => onOpenExistingRowEditor(row)}
                      >
                        Queue update
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className={
                          queuedDeleteSet.has(row.id)
                            ? "h-7 border-marketing-danger bg-marketing-danger-soft text-marketing-danger"
                            : "h-7 border-marketing-border"
                        }
                        onClick={() => onToggleQueuedDelete(row.id)}
                      >
                        {queuedDeleteSet.has(row.id)
                          ? "Undo delete"
                          : "Queue delete"}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-3">
        <div className="rounded-lg border border-marketing-border bg-marketing-accent-soft p-3">
          <div className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
            Aggregate row
          </div>
          <pre className="mt-2 overflow-x-auto text-xs text-marketing-text-secondary">
            {JSON.stringify(queryResult.aggregate_row ?? {}, null, 2)}
          </pre>
        </div>
        <div className="rounded-lg border border-marketing-border bg-marketing-accent-soft p-3">
          <div className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
            Grouped rows
          </div>
          <pre className="mt-2 overflow-x-auto text-xs text-marketing-text-secondary">
            {JSON.stringify(queryResult.grouped_rows, null, 2)}
          </pre>
        </div>
        <div className="rounded-lg border border-marketing-border bg-marketing-accent-soft p-3">
          <div className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
            Provenance
          </div>
          <pre className="mt-2 overflow-x-auto text-xs text-marketing-text-secondary">
            {JSON.stringify(queryResult.provenance, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
