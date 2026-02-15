import { type FormEvent, useCallback, useEffect, useState } from "react";
import {
  createReport,
  deleteReport,
  getReport,
  listReports,
  updateReport,
} from "@/shared/api/clients/reports.client";
import type {
  ReportCreateInput,
  ReportDetail,
  ReportSummary,
  ReportUpdateInput,
} from "@/shared/api/schemas/reports";

const parseErrorMessage = (error: unknown, fallback: string) => {
  if (error && typeof error === "object" && "message" in error) {
    return String((error as { message: unknown }).message);
  }
  return fallback;
};

const isAbortLikeError = (error: unknown, signal?: AbortSignal) =>
  signal?.aborted ||
  (error instanceof DOMException && error.name === "AbortError");

export type ReportEditorMode = "create" | "edit";

export function useReports() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editorMode, setEditorMode] = useState<ReportEditorMode>("create");
  const [selectedReport, setSelectedReport] = useState<ReportDetail | null>(
    null,
  );
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  const [title, setTitle] = useState("");
  const [preview, setPreview] = useState("");
  const [content, setContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [deletingReportId, setDeletingReportId] = useState<string | null>(null);
  const [togglingReportId, setTogglingReportId] = useState<string | null>(null);

  const refreshReports = useCallback(async (signal?: AbortSignal) => {
    setIsLoading(true);
    setError(null);
    try {
      const items = await listReports({
        includeDisabled: true,
        signal,
      });
      setReports(items);
    } catch (loadError) {
      if (isAbortLikeError(loadError, signal)) {
        return;
      }
      setError(parseErrorMessage(loadError, "Failed to load reports."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void refreshReports(controller.signal);
    return () => controller.abort();
  }, [refreshReports]);

  const closeEditor = useCallback(() => {
    setIsEditorOpen(false);
    setSelectedReport(null);
    setIsLoadingDetail(false);
    setFormError(null);
  }, []);

  const openCreateEditor = useCallback(() => {
    setEditorMode("create");
    setSelectedReport(null);
    setTitle("");
    setPreview("");
    setContent("");
    setFormError(null);
    setIsLoadingDetail(false);
    setIsEditorOpen(true);
  }, []);

  const openEditEditor = useCallback(async (reportId: string) => {
    setEditorMode("edit");
    setSelectedReport(null);
    setTitle("");
    setPreview("");
    setContent("");
    setFormError(null);
    setIsLoadingDetail(true);
    setIsEditorOpen(true);

    try {
      const detail = await getReport(reportId);
      setSelectedReport(detail);
      setTitle(detail.title);
      setPreview(detail.preview_text);
      setContent(detail.content);
    } catch (loadError) {
      setFormError(
        parseErrorMessage(loadError, "Failed to load report details."),
      );
    } finally {
      setIsLoadingDetail(false);
    }
  }, []);

  const submitEditor = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();

      const normalizedTitle = title.trim();
      const normalizedContent = content.trim();
      const normalizedPreview = preview.trim();
      if (!normalizedTitle || !normalizedContent) {
        setFormError("Title and report content are required.");
        return;
      }

      setIsSubmitting(true);
      setFormError(null);
      try {
        if (editorMode === "create") {
          const payload: ReportCreateInput = {
            title: normalizedTitle,
            content: normalizedContent,
            preview_text: normalizedPreview ? normalizedPreview : null,
            enabled_for_agent: true,
          };
          await createReport(payload);
        } else {
          if (!selectedReport) {
            return;
          }

          const payload: ReportUpdateInput = {};
          if (normalizedTitle !== selectedReport.title) {
            payload.title = normalizedTitle;
          }
          if (normalizedContent !== selectedReport.content) {
            payload.content = normalizedContent;
          }
          if (normalizedPreview !== selectedReport.preview_text) {
            payload.preview_text = normalizedPreview;
          }

          if (Object.keys(payload).length > 0) {
            await updateReport(selectedReport.id, payload);
          }
        }

        await refreshReports();
        closeEditor();
      } catch (submitError) {
        setFormError(
          parseErrorMessage(
            submitError,
            editorMode === "create"
              ? "Failed to create report."
              : "Failed to save report.",
          ),
        );
      } finally {
        setIsSubmitting(false);
      }
    },
    [
      closeEditor,
      content,
      editorMode,
      preview,
      refreshReports,
      selectedReport,
      title,
    ],
  );

  const removeReport = useCallback(
    async (report: ReportSummary) => {
      const confirmed = window.confirm(
        `Delete report "${report.title}"? This action cannot be undone.`,
      );
      if (!confirmed) {
        return;
      }

      setDeletingReportId(report.id);
      try {
        await deleteReport(report.id);
        if (selectedReport?.id === report.id) {
          closeEditor();
        }
        await refreshReports();
      } catch (deleteError) {
        window.alert(
          parseErrorMessage(deleteError, "Failed to delete report."),
        );
      } finally {
        setDeletingReportId(null);
      }
    },
    [closeEditor, refreshReports, selectedReport?.id],
  );

  const toggleAgentAccess = useCallback(
    async (report: ReportSummary) => {
      setTogglingReportId(report.id);
      try {
        const updated = await updateReport(report.id, {
          enabled_for_agent: !report.enabled_for_agent,
        });
        if (selectedReport?.id === report.id) {
          setSelectedReport(updated);
        }
        await refreshReports();
      } catch (toggleError) {
        window.alert(
          parseErrorMessage(toggleError, "Failed to update report access."),
        );
      } finally {
        setTogglingReportId(null);
      }
    },
    [refreshReports, selectedReport?.id],
  );

  return {
    refreshReports,
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
    deleteReport: removeReport,
    deletingReportId,
    toggleAgentAccess,
    togglingReportId,
  };
}
