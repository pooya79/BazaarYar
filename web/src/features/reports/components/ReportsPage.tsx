"use client";

import { Edit3, FileText, Plus, Trash2 } from "lucide-react";
import { ReportEditorModal } from "@/features/reports/components/ReportEditorModal";
import { useReports } from "@/features/reports/hooks/useReports";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeStyle: "short",
});

const formatDate = (value: string) => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return dateFormatter.format(parsed);
};

export function ReportsPage() {
  const {
    reports,
    isLoading,
    error,
    isEditorOpen,
    editorMode,
    selectedReport,
    isLoadingDetail,
    title,
    setTitle,
    preview,
    setPreview,
    content,
    setContent,
    isSubmitting,
    formError,
    openCreateEditor,
    openEditEditor,
    closeEditor,
    submitEditor,
    deleteReport,
    deletingReportId,
    toggleAgentAccess,
    togglingReportId,
  } = useReports();

  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-6 py-6 md:px-10 md:py-8">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-4">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-marketing-text-primary">
              Conversation Reports
            </h1>
            <p className="mt-1 text-sm text-marketing-text-secondary">
              Saved reports can be retrieved and used by the AI assistant in
              future conversations.
            </p>
          </div>
          <Button
            type="button"
            size="icon"
            className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
            onClick={openCreateEditor}
            aria-label="Create report"
          >
            <Plus className="size-4" aria-hidden="true" />
          </Button>
        </header>

        <section className="rounded-2xl border border-marketing-border bg-marketing-surface p-4 shadow-marketing-subtle">
          {isLoading ? (
            <div className="rounded-lg border border-marketing-border bg-marketing-bg px-3 py-4 text-sm text-marketing-text-muted">
              Loading reports...
            </div>
          ) : null}

          {error ? (
            <div className="mb-3 rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
              {error}
            </div>
          ) : null}

          {!isLoading && reports.length === 0 ? (
            <div className="rounded-lg border border-dashed border-marketing-border bg-marketing-bg px-3 py-6 text-center text-sm text-marketing-text-muted">
              No reports yet. Click the plus button to create one.
            </div>
          ) : null}

          <div className="grid gap-3 md:grid-cols-2">
            {reports.map((report) => (
              <article
                key={report.id}
                className="rounded-xl border border-marketing-border bg-marketing-bg p-3"
              >
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <FileText
                        className="size-4 shrink-0 text-marketing-primary"
                        aria-hidden="true"
                      />
                      <h2 className="truncate text-sm font-semibold text-marketing-text-primary">
                        {report.title}
                      </h2>
                    </div>
                    <p className="mt-1 line-clamp-2 text-sm text-marketing-text-secondary">
                      {report.preview_text || "No preview"}
                    </p>
                  </div>
                  <span
                    className={cn(
                      "inline-flex shrink-0 items-center rounded-full border px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-[0.06em]",
                      report.enabled_for_agent
                        ? "border-marketing-status-active/25 bg-marketing-status-active/10 text-marketing-status-active"
                        : "border-marketing-status-draft/25 bg-marketing-status-draft/10 text-marketing-status-draft",
                    )}
                  >
                    {report.enabled_for_agent
                      ? "Agent Enabled"
                      : "Agent Disabled"}
                  </span>
                </div>

                <div className="mb-3 flex flex-wrap gap-3 text-xs text-marketing-text-muted">
                  <span>Updated: {formatDate(report.updated_at)}</span>
                  <span>Created: {formatDate(report.created_at)}</span>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="border-marketing-border"
                    onClick={() => {
                      void openEditEditor(report.id);
                    }}
                  >
                    <Edit3 className="size-4" aria-hidden="true" />
                    Edit
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="border-marketing-border"
                    onClick={() => {
                      void toggleAgentAccess(report);
                    }}
                    disabled={togglingReportId === report.id}
                  >
                    {togglingReportId === report.id
                      ? "Updating..."
                      : report.enabled_for_agent
                        ? "Disable Agent Access"
                        : "Enable Agent Access"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="border-marketing-danger text-marketing-danger hover:bg-marketing-danger-soft"
                    onClick={() => {
                      void deleteReport(report);
                    }}
                    disabled={deletingReportId === report.id}
                  >
                    <Trash2 className="size-4" aria-hidden="true" />
                    {deletingReportId === report.id ? "Deleting..." : "Delete"}
                  </Button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>

      <ReportEditorModal
        open={isEditorOpen}
        mode={editorMode}
        isLoadingDetail={isLoadingDetail}
        isEditorReady={editorMode === "create" || Boolean(selectedReport)}
        title={title}
        preview={preview}
        content={content}
        onTitleChange={setTitle}
        onPreviewChange={setPreview}
        onContentChange={setContent}
        isSubmitting={isSubmitting}
        formError={formError}
        onOpenChange={(open) => {
          if (!open) {
            closeEditor();
          }
        }}
        onCancel={closeEditor}
        onSubmit={submitEditor}
      />
    </div>
  );
}
