"use client";

import { Edit3, FileText, Search, Trash2 } from "lucide-react";
import { useReports } from "@/features/reports/hooks/useReports";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { Textarea } from "@/shared/ui/textarea";

const fieldClass =
  "h-10 w-full rounded-lg border border-marketing-border bg-marketing-surface px-3 text-sm text-marketing-text-primary outline-none transition-colors focus:border-marketing-primary";

const labelClass =
  "text-[0.68rem] font-semibold uppercase tracking-[0.08em] text-marketing-text-muted";

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
    refreshReports,
    reports,
    isLoading,
    error,
    searchQuery,
    setSearchQuery,
    activeQuery,
    submitSearch,
    clearSearch,
    createTitle,
    setCreateTitle,
    createPreview,
    setCreatePreview,
    createContent,
    setCreateContent,
    createEnabled,
    setCreateEnabled,
    isCreating,
    createError,
    submitCreate,
    selectedReport,
    isLoadingDetail,
    openReportEditor,
    closeReportEditor,
    editTitle,
    setEditTitle,
    editPreview,
    setEditPreview,
    editContent,
    setEditContent,
    editEnabled,
    setEditEnabled,
    isSavingEdit,
    editError,
    submitEdit,
    deleteReport,
    deletingReportId,
    toggleAgentAccess,
    togglingReportId,
  } = useReports();

  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-6 py-6 md:px-10 md:py-8">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
        <section className="rounded-2xl border border-marketing-border bg-marketing-surface p-4 shadow-marketing-subtle">
          <form
            onSubmit={submitSearch}
            className="flex flex-col gap-3 md:flex-row md:items-end"
          >
            <div className="flex-1 space-y-1">
              <label className={labelClass} htmlFor="reports-search">
                Search reports
              </label>
              <div className="relative">
                <Search
                  className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-marketing-text-muted"
                  aria-hidden="true"
                />
                <input
                  id="reports-search"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Search by title, preview, or report content..."
                  className={cn(fieldClass, "pl-9")}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button type="submit">Search</Button>
              <Button type="button" variant="outline" onClick={clearSearch}>
                Clear
              </Button>
            </div>
          </form>
          {activeQuery ? (
            <p className="mt-3 text-xs text-marketing-text-muted">
              Showing results for "{activeQuery}".
            </p>
          ) : null}
        </section>

        <section className="rounded-2xl border border-marketing-border bg-marketing-surface p-4 shadow-marketing-subtle">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-marketing-text-primary">
              Create Conversation Report
            </h2>
            <label className="inline-flex items-center gap-2 text-xs text-marketing-text-secondary">
              <input
                type="checkbox"
                checked={createEnabled}
                onChange={(event) => setCreateEnabled(event.target.checked)}
              />
              Enabled for agent retrieval
            </label>
          </div>

          <form onSubmit={submitCreate} className="space-y-3">
            <div className="space-y-1">
              <label className={labelClass} htmlFor="report-create-title">
                Title
              </label>
              <input
                id="report-create-title"
                className={fieldClass}
                value={createTitle}
                onChange={(event) => setCreateTitle(event.target.value)}
                placeholder="Q1 Campaign Retrospective"
              />
            </div>
            <div className="space-y-1">
              <label className={labelClass} htmlFor="report-create-preview">
                Preview (optional)
              </label>
              <input
                id="report-create-preview"
                className={fieldClass}
                value={createPreview}
                onChange={(event) => setCreatePreview(event.target.value)}
                maxLength={180}
                placeholder="Short one-line snapshot of this report..."
              />
            </div>
            <div className="space-y-1">
              <label className={labelClass} htmlFor="report-create-content">
                Report content
              </label>
              <Textarea
                id="report-create-content"
                className="min-h-36 border-marketing-border text-marketing-text-primary"
                value={createContent}
                onChange={(event) => setCreateContent(event.target.value)}
                placeholder="Write the report summary you want to save for future agent conversations."
              />
            </div>
            {createError ? (
              <div className="rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
                {createError}
              </div>
            ) : null}
            <div className="flex justify-end">
              <Button type="submit" disabled={isCreating}>
                {isCreating ? "Creating..." : "Create Report"}
              </Button>
            </div>
          </form>
        </section>

        <section className="rounded-2xl border border-marketing-border bg-marketing-surface p-4 shadow-marketing-subtle">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-marketing-text-primary">
              Saved Reports
            </h2>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                void refreshReports();
              }}
            >
              Refresh
            </Button>
          </div>

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
              No reports yet. Create one above or ask the agent to save one.
            </div>
          ) : null}

          <div className="space-y-3">
            {reports.map((report) => (
              <article
                key={report.id}
                className={cn(
                  "rounded-xl border border-marketing-border bg-marketing-bg p-3",
                  selectedReport?.id === report.id &&
                    "border-marketing-primary ring-1 ring-marketing-accent-ring/60",
                )}
              >
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <FileText
                        className="size-4 shrink-0 text-marketing-primary"
                        aria-hidden="true"
                      />
                      <h3 className="truncate text-sm font-semibold text-marketing-text-primary">
                        {report.title}
                      </h3>
                    </div>
                    <p className="mt-1 text-sm text-marketing-text-secondary">
                      {report.preview_text}
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
                  <span>Created: {formatDate(report.created_at)}</span>
                  <span>Updated: {formatDate(report.updated_at)}</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="border-marketing-border"
                    onClick={() => {
                      void openReportEditor(report.id);
                    }}
                  >
                    <Edit3 className="size-4" aria-hidden="true" />
                    Open
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

        <section className="rounded-2xl border border-marketing-border bg-marketing-surface p-4 shadow-marketing-subtle">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-marketing-text-primary">
              Edit Report
            </h2>
            {selectedReport ? (
              <Button
                type="button"
                variant="outline"
                onClick={closeReportEditor}
              >
                Close
              </Button>
            ) : null}
          </div>

          {isLoadingDetail ? (
            <div className="rounded-lg border border-marketing-border bg-marketing-bg px-3 py-4 text-sm text-marketing-text-muted">
              Loading report details...
            </div>
          ) : null}

          {!isLoadingDetail && !selectedReport ? (
            <div className="rounded-lg border border-dashed border-marketing-border bg-marketing-bg px-3 py-6 text-center text-sm text-marketing-text-muted">
              Select a report from the list to edit it.
            </div>
          ) : null}

          {selectedReport ? (
            <form onSubmit={submitEdit} className="space-y-3">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-1">
                  <div className={labelClass}>Created</div>
                  <div className="rounded-lg border border-marketing-border bg-marketing-bg px-3 py-2 text-sm text-marketing-text-secondary">
                    {formatDate(selectedReport.created_at)}
                  </div>
                </div>
                <div className="space-y-1">
                  <div className={labelClass}>Source conversation</div>
                  <div className="rounded-lg border border-marketing-border bg-marketing-bg px-3 py-2 text-sm text-marketing-text-secondary">
                    {selectedReport.source_conversation_id ?? "None"}
                  </div>
                </div>
              </div>

              <div className="space-y-1">
                <label className={labelClass} htmlFor="report-edit-title">
                  Title
                </label>
                <input
                  id="report-edit-title"
                  className={fieldClass}
                  value={editTitle}
                  onChange={(event) => setEditTitle(event.target.value)}
                />
              </div>

              <div className="space-y-1">
                <label className={labelClass} htmlFor="report-edit-preview">
                  Preview
                </label>
                <input
                  id="report-edit-preview"
                  className={fieldClass}
                  value={editPreview}
                  onChange={(event) => setEditPreview(event.target.value)}
                  maxLength={180}
                />
              </div>

              <div className="space-y-1">
                <label className={labelClass} htmlFor="report-edit-content">
                  Report content
                </label>
                <Textarea
                  id="report-edit-content"
                  className="min-h-36 border-marketing-border text-marketing-text-primary"
                  value={editContent}
                  onChange={(event) => setEditContent(event.target.value)}
                />
              </div>

              <label className="inline-flex items-center gap-2 text-xs text-marketing-text-secondary">
                <input
                  type="checkbox"
                  checked={editEnabled}
                  onChange={(event) => setEditEnabled(event.target.checked)}
                />
                Enabled for agent retrieval
              </label>

              {editError ? (
                <div className="rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
                  {editError}
                </div>
              ) : null}

              <div className="flex justify-end">
                <Button type="submit" disabled={isSavingEdit}>
                  {isSavingEdit ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </form>
          ) : null}
        </section>
      </div>
    </div>
  );
}
