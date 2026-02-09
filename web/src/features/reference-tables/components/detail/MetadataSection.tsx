import { ArrowLeft, Download, Loader2, Pencil } from "lucide-react";
import type { FormEvent } from "react";
import {
  fieldClass,
  panelClass,
} from "@/features/reference-tables/model/queryDrafts";
import { formatDateTime } from "@/features/reference-tables/utils/tableUtils";
import type { ReferenceTableDetail } from "@/shared/api/schemas/tables";
import { Button } from "@/shared/ui/button";

type MetadataSectionProps = {
  table: ReferenceTableDetail;
  isEditingMetadata: boolean;
  metadataTitle: string;
  metadataDescription: string;
  metadataError: string | null;
  isSavingMetadata: boolean;
  isExporting: boolean;
  onBack: () => void;
  onToggleEditMetadata: () => void;
  onMetadataTitleChange: (value: string) => void;
  onMetadataDescriptionChange: (value: string) => void;
  onSaveMetadata: (event: FormEvent<HTMLFormElement>) => void;
  onCancelMetadataEdit: () => void;
  onExport: () => void;
};

export function MetadataSection({
  table,
  isEditingMetadata,
  metadataTitle,
  metadataDescription,
  metadataError,
  isSavingMetadata,
  isExporting,
  onBack,
  onToggleEditMetadata,
  onMetadataTitleChange,
  onMetadataDescriptionChange,
  onSaveMetadata,
  onCancelMetadataEdit,
  onExport,
}: MetadataSectionProps) {
  return (
    <div className={panelClass}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Button
            type="button"
            variant="ghost"
            className="-ml-2 h-8 px-2 text-marketing-text-secondary hover:bg-marketing-accent-soft hover:text-marketing-primary"
            onClick={onBack}
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back
          </Button>
          <h2 className="mt-1 text-2xl font-semibold text-marketing-text-primary">
            {table.title?.trim() || table.name}
          </h2>
          <p className="mt-1 text-sm text-marketing-text-secondary">
            {table.description?.trim() || "No description set."}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            className="border-marketing-border bg-marketing-surface"
            onClick={onToggleEditMetadata}
          >
            <Pencil className="size-4" aria-hidden="true" />
            {isEditingMetadata ? "Close metadata editor" : "Edit metadata"}
          </Button>
          <Button
            type="button"
            className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
            onClick={onExport}
            disabled={isExporting}
          >
            {isExporting ? (
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            ) : (
              <Download className="size-4" aria-hidden="true" />
            )}
            Export
          </Button>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        {[
          { label: "Rows", value: table.row_count.toLocaleString() },
          { label: "Columns", value: table.columns.length.toString() },
          { label: "Created", value: formatDateTime(table.created_at) },
          { label: "Updated", value: formatDateTime(table.updated_at) },
        ].map((item) => (
          <div
            key={item.label}
            className="rounded-xl border border-marketing-border bg-marketing-accent-soft px-3 py-2"
          >
            <div className="text-xs uppercase tracking-[1px] text-marketing-text-muted">
              {item.label}
            </div>
            <div className="text-sm font-semibold text-marketing-text-primary">
              {item.value}
            </div>
          </div>
        ))}
      </div>

      {isEditingMetadata && (
        <form onSubmit={onSaveMetadata} className="mt-4 space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <label
                htmlFor="metadata-title"
                className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted"
              >
                Title
              </label>
              <input
                id="metadata-title"
                className={fieldClass}
                value={metadataTitle}
                onChange={(event) => onMetadataTitleChange(event.target.value)}
                placeholder="Table title"
              />
            </div>
            <div className="space-y-1">
              <label
                htmlFor="metadata-description"
                className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted"
              >
                Description
              </label>
              <input
                id="metadata-description"
                className={fieldClass}
                value={metadataDescription}
                onChange={(event) =>
                  onMetadataDescriptionChange(event.target.value)
                }
                placeholder="Table description"
              />
            </div>
          </div>

          {metadataError && (
            <div className="rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
              {metadataError}
            </div>
          )}

          <div className="flex gap-2">
            <Button
              type="submit"
              disabled={isSavingMetadata}
              className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
            >
              {isSavingMetadata ? "Saving..." : "Save metadata"}
            </Button>
            <Button
              type="button"
              variant="outline"
              className="border-marketing-border"
              onClick={onCancelMetadataEdit}
            >
              Cancel
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
