import { Loader2, Plus, Save, Trash2, X } from "lucide-react";
import type { QueuedUpsert } from "@/features/reference-tables/model/queryDrafts";
import { panelClass } from "@/features/reference-tables/model/queryDrafts";
import { Button } from "@/shared/ui/button";

type RowMutationsSectionProps = {
  queuedUpserts: QueuedUpsert[];
  queuedDeleteRowIds: string[];
  batchError: string | null;
  batchValidationErrors: string[];
  batchSuccess: string | null;
  isSavingBatch: boolean;
  queryPage: number;
  onOpenNewRowEditor: () => void;
  onClearQueue: () => void;
  onSaveQueuedMutations: () => void;
  onRemoveQueuedUpsert: (clientId: string) => void;
};

export function RowMutationsSection({
  queuedUpserts,
  queuedDeleteRowIds,
  batchError,
  batchValidationErrors,
  batchSuccess,
  isSavingBatch,
  queryPage,
  onOpenNewRowEditor,
  onClearQueue,
  onSaveQueuedMutations,
  onRemoveQueuedUpsert,
}: RowMutationsSectionProps) {
  return (
    <div className={panelClass}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-base font-semibold text-marketing-text-primary">
          Row mutation queue
        </h3>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            className="border-marketing-border"
            onClick={onOpenNewRowEditor}
          >
            <Plus className="size-4" aria-hidden="true" />
            Queue new row
          </Button>
          <Button
            type="button"
            variant="outline"
            className="border-marketing-border"
            onClick={onClearQueue}
          >
            <X className="size-4" aria-hidden="true" />
            Clear queue
          </Button>
          <Button
            type="button"
            className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
            onClick={onSaveQueuedMutations}
            disabled={isSavingBatch}
          >
            {isSavingBatch ? (
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            ) : (
              <Save className="size-4" aria-hidden="true" />
            )}
            Save queued changes
          </Button>
        </div>
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        <div className="rounded-lg border border-marketing-border bg-marketing-accent-soft px-3 py-2 text-sm text-marketing-text-secondary">
          Upserts queued: {queuedUpserts.length}
        </div>
        <div className="rounded-lg border border-marketing-border bg-marketing-accent-soft px-3 py-2 text-sm text-marketing-text-secondary">
          Deletes queued: {queuedDeleteRowIds.length}
        </div>
        <div className="rounded-lg border border-marketing-border bg-marketing-accent-soft px-3 py-2 text-sm text-marketing-text-secondary">
          Last query page: {queryPage}
        </div>
      </div>

      {queuedUpserts.length > 0 && (
        <div className="mt-3 space-y-2">
          <div className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
            Queued upserts
          </div>
          {queuedUpserts.map((item) => (
            <div
              key={item.client_id}
              className="rounded-lg border border-marketing-border bg-marketing-accent-soft p-2"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="text-xs font-semibold text-marketing-text-secondary">
                  {item.row_id ? `Row ${item.row_id}` : "New row"}
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-xs"
                  className="text-marketing-danger hover:bg-marketing-danger-soft"
                  onClick={() => onRemoveQueuedUpsert(item.client_id)}
                >
                  <Trash2 className="size-3" aria-hidden="true" />
                </Button>
              </div>
              <pre className="mt-1 overflow-x-auto text-xs text-marketing-text-secondary">
                {JSON.stringify(item.values_json, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}

      {queuedDeleteRowIds.length > 0 && (
        <div className="mt-3 rounded-lg border border-marketing-border bg-marketing-accent-soft p-3">
          <div className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
            Queued deletes
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {queuedDeleteRowIds.map((rowId) => (
              <span
                key={rowId}
                className="rounded-full border border-marketing-danger bg-marketing-danger-soft px-2 py-1 text-xs font-semibold text-marketing-danger"
              >
                {rowId}
              </span>
            ))}
          </div>
        </div>
      )}

      {batchError && (
        <div className="mt-3 rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
          {batchError}
        </div>
      )}

      {batchValidationErrors.length > 0 && (
        <div className="mt-3 rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
          <p className="font-semibold">Validation errors</p>
          <ul className="mt-2 list-disc pl-5">
            {batchValidationErrors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      {batchSuccess && (
        <div className="mt-3 rounded-lg border border-marketing-status-active/40 bg-marketing-accent-soft px-3 py-2 text-sm text-marketing-text-primary">
          {batchSuccess}
        </div>
      )}
    </div>
  );
}
