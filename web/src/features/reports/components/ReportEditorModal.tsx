"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { FormEvent } from "react";
import type { ReportEditorMode } from "@/features/reports/hooks/useReports";
import { Button } from "@/shared/ui/button";
import { Textarea } from "@/shared/ui/textarea";

const fieldClass =
  "h-10 w-full rounded-lg border border-marketing-border bg-marketing-surface px-3 text-sm text-marketing-text-primary outline-none transition-colors focus:border-marketing-primary";

const labelClass =
  "text-[0.68rem] font-semibold uppercase tracking-[0.08em] text-marketing-text-muted";

type ReportEditorModalProps = {
  open: boolean;
  mode: ReportEditorMode;
  isLoadingDetail: boolean;
  isEditorReady: boolean;
  title: string;
  preview: string;
  content: string;
  onTitleChange: (value: string) => void;
  onPreviewChange: (value: string) => void;
  onContentChange: (value: string) => void;
  isSubmitting: boolean;
  formError: string | null;
  onOpenChange: (open: boolean) => void;
  onCancel: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

export function ReportEditorModal({
  open,
  mode,
  isLoadingDetail,
  isEditorReady,
  title,
  preview,
  content,
  onTitleChange,
  onPreviewChange,
  onContentChange,
  isSubmitting,
  formError,
  onOpenChange,
  onCancel,
  onSubmit,
}: ReportEditorModalProps) {
  const isCreateMode = mode === "create";
  const showForm = isCreateMode || isEditorReady;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[140] bg-black/60 backdrop-blur-[1px]" />
        <Dialog.Content className="fixed top-1/2 left-1/2 z-[150] flex h-[min(90vh,44rem)] w-[min(94vw,46rem)] -translate-x-1/2 -translate-y-1/2 flex-col rounded-2xl border border-marketing-border bg-marketing-surface shadow-marketing-glow">
          <div className="flex items-start justify-between border-b border-marketing-border p-5">
            <div>
              <Dialog.Title className="text-lg font-semibold text-marketing-text-primary">
                {isCreateMode ? "Create report" : "Edit report"}
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-marketing-text-secondary">
                {isCreateMode
                  ? "Add a conversation report to your saved reports list."
                  : "Update report title, preview, and content."}
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="inline-flex size-9 items-center justify-center rounded-lg border border-marketing-border bg-marketing-surface text-marketing-text-secondary transition-colors hover:text-marketing-text-primary"
                aria-label="Close"
              >
                <X className="size-4" aria-hidden="true" />
              </button>
            </Dialog.Close>
          </div>

          {isLoadingDetail ? (
            <div className="p-5">
              <div className="rounded-lg border border-marketing-border bg-marketing-bg px-3 py-4 text-sm text-marketing-text-muted">
                Loading report details...
              </div>
            </div>
          ) : null}

          {!isLoadingDetail && !showForm ? (
            <div className="p-5">
              <div className="rounded-lg border border-dashed border-marketing-border bg-marketing-bg px-3 py-6 text-center text-sm text-marketing-text-muted">
                Unable to load report details.
              </div>
              {formError ? (
                <div className="mt-3 rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
                  {formError}
                </div>
              ) : null}
            </div>
          ) : null}

          {showForm ? (
            <form onSubmit={onSubmit} className="flex min-h-0 flex-1 flex-col">
              <div className="flex-1 space-y-4 overflow-y-auto p-5">
                <div className="space-y-1">
                  <label className={labelClass} htmlFor="report-modal-title">
                    Title
                  </label>
                  <input
                    id="report-modal-title"
                    className={fieldClass}
                    value={title}
                    onChange={(event) => onTitleChange(event.target.value)}
                    placeholder="Q1 Campaign Retrospective"
                  />
                </div>

                <div className="space-y-1">
                  <label className={labelClass} htmlFor="report-modal-preview">
                    Preview (optional)
                  </label>
                  <input
                    id="report-modal-preview"
                    className={fieldClass}
                    value={preview}
                    onChange={(event) => onPreviewChange(event.target.value)}
                    maxLength={180}
                    placeholder="Short one-line snapshot of this report..."
                  />
                </div>

                <div className="space-y-1">
                  <label className={labelClass} htmlFor="report-modal-content">
                    Report content
                  </label>
                  <Textarea
                    id="report-modal-content"
                    className="min-h-40 border-marketing-border text-marketing-text-primary"
                    value={content}
                    onChange={(event) => onContentChange(event.target.value)}
                    placeholder="Write the report summary you want to save for future agent conversations."
                  />
                </div>

                {formError ? (
                  <div className="rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
                    {formError}
                  </div>
                ) : null}
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-marketing-border p-5">
                <Button
                  type="button"
                  variant="outline"
                  className="border-marketing-border"
                  onClick={onCancel}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
                >
                  {isSubmitting
                    ? isCreateMode
                      ? "Creating..."
                      : "Saving..."
                    : isCreateMode
                      ? "Create report"
                      : "Save changes"}
                </Button>
              </div>
            </form>
          ) : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
