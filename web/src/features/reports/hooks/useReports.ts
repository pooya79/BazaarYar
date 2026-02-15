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

export function useReports() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [activeQuery, setActiveQuery] = useState("");

  const [createTitle, setCreateTitle] = useState("");
  const [createPreview, setCreatePreview] = useState("");
  const [createContent, setCreateContent] = useState("");
  const [createEnabled, setCreateEnabled] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [selectedReport, setSelectedReport] = useState<ReportDetail | null>(
    null,
  );
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editPreview, setEditPreview] = useState("");
  const [editContent, setEditContent] = useState("");
  const [editEnabled, setEditEnabled] = useState(true);
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const [deletingReportId, setDeletingReportId] = useState<string | null>(null);
  const [togglingReportId, setTogglingReportId] = useState<string | null>(null);

  const refreshReports = useCallback(
    async (signal?: AbortSignal) => {
      setIsLoading(true);
      setError(null);
      try {
        const items = await listReports({
          q: activeQuery,
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
    },
    [activeQuery],
  );

  useEffect(() => {
    const controller = new AbortController();
    void refreshReports(controller.signal);
    return () => controller.abort();
  }, [refreshReports]);

  const openReportEditor = useCallback(async (reportId: string) => {
    setIsLoadingDetail(true);
    setEditError(null);
    try {
      const detail = await getReport(reportId);
      setSelectedReport(detail);
      setEditTitle(detail.title);
      setEditPreview(detail.preview_text);
      setEditContent(detail.content);
      setEditEnabled(detail.enabled_for_agent);
    } catch (loadError) {
      setEditError(
        parseErrorMessage(loadError, "Failed to load report details."),
      );
    } finally {
      setIsLoadingDetail(false);
    }
  }, []);

  const closeReportEditor = useCallback(() => {
    setSelectedReport(null);
    setEditError(null);
  }, []);

  const submitSearch = useCallback(
    (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setActiveQuery(searchQuery.trim());
    },
    [searchQuery],
  );

  const clearSearch = useCallback(() => {
    setSearchQuery("");
    setActiveQuery("");
  }, []);

  const submitCreate = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const title = createTitle.trim();
      const content = createContent.trim();
      const preview = createPreview.trim();

      if (!title || !content) {
        setCreateError("Title and report content are required.");
        return;
      }

      const payload: ReportCreateInput = {
        title,
        content,
        preview_text: preview ? preview : null,
        enabled_for_agent: createEnabled,
      };

      setIsCreating(true);
      setCreateError(null);
      try {
        const created = await createReport(payload);
        setCreateTitle("");
        setCreatePreview("");
        setCreateContent("");
        setCreateEnabled(true);
        setSelectedReport(created);
        setEditTitle(created.title);
        setEditPreview(created.preview_text);
        setEditContent(created.content);
        setEditEnabled(created.enabled_for_agent);
        await refreshReports();
      } catch (submitError) {
        setCreateError(
          parseErrorMessage(submitError, "Failed to create report."),
        );
      } finally {
        setIsCreating(false);
      }
    },
    [createContent, createEnabled, createPreview, createTitle, refreshReports],
  );

  const submitEdit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!selectedReport) {
        return;
      }

      const title = editTitle.trim();
      const content = editContent.trim();
      const preview = editPreview.trim();
      if (!title || !content) {
        setEditError("Title and report content are required.");
        return;
      }

      const payload: ReportUpdateInput = {};
      if (title !== selectedReport.title) {
        payload.title = title;
      }
      if (content !== selectedReport.content) {
        payload.content = content;
      }
      if (preview !== selectedReport.preview_text) {
        payload.preview_text = preview;
      }
      if (editEnabled !== selectedReport.enabled_for_agent) {
        payload.enabled_for_agent = editEnabled;
      }

      if (Object.keys(payload).length === 0) {
        return;
      }

      setIsSavingEdit(true);
      setEditError(null);
      try {
        const updated = await updateReport(selectedReport.id, payload);
        setSelectedReport(updated);
        setEditTitle(updated.title);
        setEditPreview(updated.preview_text);
        setEditContent(updated.content);
        setEditEnabled(updated.enabled_for_agent);
        await refreshReports();
      } catch (submitError) {
        setEditError(parseErrorMessage(submitError, "Failed to save report."));
      } finally {
        setIsSavingEdit(false);
      }
    },
    [
      editContent,
      editEnabled,
      editPreview,
      editTitle,
      refreshReports,
      selectedReport,
    ],
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
          setEditEnabled(updated.enabled_for_agent);
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
          closeReportEditor();
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
    [closeReportEditor, refreshReports, selectedReport?.id],
  );

  return {
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
    deleteReport: removeReport,
    deletingReportId,
    toggleAgentAccess,
    togglingReportId,
  };
}
