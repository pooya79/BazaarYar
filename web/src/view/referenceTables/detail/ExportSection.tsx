import { Download, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ExportFormat } from "@/lib/api/schemas/tables";
import { panelClass } from "./constants";

type ExportSectionProps = {
  exportFormat: ExportFormat;
  includeHeader: boolean;
  includeCurrentQuery: boolean;
  isExporting: boolean;
  exportError: string | null;
  onExportFormatChange: (value: ExportFormat) => void;
  onIncludeHeaderChange: (value: boolean) => void;
  onIncludeCurrentQueryChange: (value: boolean) => void;
  onRunExport: () => void;
};

export function ExportSection({
  exportFormat,
  includeHeader,
  includeCurrentQuery,
  isExporting,
  exportError,
  onExportFormatChange,
  onIncludeHeaderChange,
  onIncludeCurrentQueryChange,
  onRunExport,
}: ExportSectionProps) {
  return (
    <div className={panelClass}>
      <h3 className="text-base font-semibold text-marketing-text-primary">
        Export
      </h3>
      <p className="mt-1 text-sm text-marketing-text-secondary">
        Export the full table or the current filtered query view.
      </p>

      <div className="mt-3 space-y-3">
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
            Format
          </p>
          <Select
            value={exportFormat}
            onValueChange={(value) =>
              onExportFormatChange(value as ExportFormat)
            }
          >
            <SelectTrigger className="h-9 w-full border-marketing-border bg-marketing-surface">
              <SelectValue placeholder="Format" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="csv">CSV</SelectItem>
              <SelectItem value="json">JSON</SelectItem>
              <SelectItem value="xlsx">XLSX</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <label className="flex items-center gap-2 text-sm text-marketing-text-secondary">
          <input
            type="checkbox"
            checked={includeHeader}
            onChange={(event) => onIncludeHeaderChange(event.target.checked)}
            className="size-4 rounded border-marketing-border"
          />
          Include header row
        </label>

        <label className="flex items-center gap-2 text-sm text-marketing-text-secondary">
          <input
            type="checkbox"
            checked={includeCurrentQuery}
            onChange={(event) =>
              onIncludeCurrentQueryChange(event.target.checked)
            }
            className="size-4 rounded border-marketing-border"
          />
          Include current query payload (filters/sorts/group/aggregates)
        </label>

        <Button
          type="button"
          className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
          onClick={onRunExport}
          disabled={isExporting}
        >
          {isExporting ? (
            <Loader2 className="size-4 animate-spin" aria-hidden="true" />
          ) : (
            <Download className="size-4" aria-hidden="true" />
          )}
          Export file
        </Button>
      </div>

      {exportError && (
        <div className="mt-3 rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
          {exportError}
        </div>
      )}
    </div>
  );
}
