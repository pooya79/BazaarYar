import { FileUp, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ImportJobSummary } from "@/lib/api/schemas/tables";
import { panelClass } from "./constants";

type ImportSectionProps = {
  isImporting: boolean;
  importError: string | null;
  importJob: ImportJobSummary | null;
  canStartImport: boolean;
  onFileChange: (file: File | null) => void;
  onStartImport: () => void;
};

export function ImportSection({
  isImporting,
  importError,
  importJob,
  canStartImport,
  onFileChange,
  onStartImport,
}: ImportSectionProps) {
  return (
    <div className={panelClass}>
      <h3 className="text-base font-semibold text-marketing-text-primary">
        Import from uploaded file
      </h3>
      <p className="mt-1 text-sm text-marketing-text-secondary">
        File is uploaded through `/api/agent/attachments`, then imported into
        this table.
      </p>

      <div className="mt-3 space-y-3">
        <input
          type="file"
          accept=".csv,.json,.xlsx"
          onChange={(event) => {
            const file = event.target.files?.[0] ?? null;
            onFileChange(file);
          }}
          className="block w-full rounded-lg border border-marketing-border bg-marketing-surface px-3 py-2 text-sm text-marketing-text-secondary file:mr-3 file:rounded-md file:border-0 file:bg-marketing-accent-soft file:px-3 file:py-1 file:text-sm file:font-semibold file:text-marketing-primary"
        />

        <Button
          type="button"
          className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
          onClick={onStartImport}
          disabled={isImporting || !canStartImport}
        >
          {isImporting ? (
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            <FileUp className="size-4" aria-hidden="true" />
          )}
          Start import
        </Button>
      </div>

      {importError && (
        <div className="mt-3 rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
          {importError}
        </div>
      )}

      {importJob && (
        <div className="mt-3 rounded-lg border border-marketing-border bg-marketing-accent-soft p-3 text-sm">
          <div className="grid grid-cols-2 gap-2 text-marketing-text-secondary">
            <span>Status</span>
            <span className="font-semibold text-marketing-text-primary">
              {importJob.status}
            </span>
            <span>Total rows</span>
            <span>{importJob.total_rows}</span>
            <span>Inserted</span>
            <span>{importJob.inserted_rows}</span>
            <span>Updated</span>
            <span>{importJob.updated_rows}</span>
            <span>Errors</span>
            <span>{importJob.error_count}</span>
          </div>

          {(importJob.inferred_columns?.length ?? 0) > 0 && (
            <div className="mt-3">
              <div className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
                Inferred columns
              </div>
              <pre className="mt-1 overflow-x-auto text-xs text-marketing-text-secondary">
                {JSON.stringify(importJob.inferred_columns, null, 2)}
              </pre>
            </div>
          )}

          {importJob.errors_json.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
                Import errors
              </div>
              <pre className="mt-1 overflow-x-auto text-xs text-marketing-text-secondary">
                {JSON.stringify(importJob.errors_json, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
