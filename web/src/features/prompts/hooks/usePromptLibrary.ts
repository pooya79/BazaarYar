"use client";

import type { FormEvent } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  normalizePromptCommandName,
  PROMPT_COMMAND_PATTERN,
} from "@/features/prompts/model/promptStore";
import type { PromptTemplate } from "@/features/prompts/model/types";
import {
  createPrompt,
  deletePrompt,
  getPrompt,
  listPrompts,
  updatePrompt,
} from "@/shared/api/clients/prompts.client";
import type {
  PromptCreateInput,
  PromptDetail,
  PromptSummary,
  PromptUpdateInput,
} from "@/shared/api/schemas/prompts";

const parseErrorMessage = (error: unknown, fallback: string) => {
  if (error && typeof error === "object" && "message" in error) {
    return String((error as { message: unknown }).message);
  }
  return fallback;
};

const isAbortLikeError = (error: unknown, signal?: AbortSignal) =>
  signal?.aborted ||
  (error instanceof DOMException && error.name === "AbortError");

const toPromptTemplate = (
  prompt: PromptSummary | PromptDetail,
): PromptTemplate => ({
  id: prompt.id,
  name: prompt.name,
  description: prompt.description,
  prompt: prompt.prompt,
  created_at: prompt.created_at,
  updated_at: prompt.updated_at,
});

export type PromptEditorMode = "create" | "edit";

type UsePromptLibraryResult = {
  prompts: PromptTemplate[];
  isLoading: boolean;
  error: string | null;
  isEditorOpen: boolean;
  editorMode: PromptEditorMode;
  expandedPromptId: string | null;
  selectedPrompt: PromptTemplate | null;
  commandName: string;
  description: string;
  promptBody: string;
  formError: string | null;
  isSubmitting: boolean;
  deletingPromptId: string | null;
  setCommandName: (value: string) => void;
  setDescription: (value: string) => void;
  setPromptBody: (value: string) => void;
  setExpandedPromptId: (promptId: string | null) => void;
  openCreateEditor: () => void;
  openEditEditor: (promptId: string) => void;
  closeEditor: () => void;
  submitEditor: (event: FormEvent<HTMLFormElement>) => void;
  deletePrompt: (promptId: string) => void;
};

export function usePromptLibrary(): UsePromptLibraryResult {
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editorMode, setEditorMode] = useState<PromptEditorMode>("create");
  const [selectedPrompt, setSelectedPrompt] = useState<PromptTemplate | null>(
    null,
  );
  const [expandedPromptId, setExpandedPromptId] = useState<string | null>(null);
  const [commandName, setCommandName] = useState("");
  const [description, setDescription] = useState("");
  const [promptBody, setPromptBody] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [deletingPromptId, setDeletingPromptId] = useState<string | null>(null);

  const refreshPrompts = useCallback(async (signal?: AbortSignal) => {
    setIsLoading(true);
    setError(null);
    try {
      const items = await listPrompts({ signal, limit: 100 });
      setPrompts(items.map(toPromptTemplate));
    } catch (loadError) {
      if (isAbortLikeError(loadError, signal)) {
        return;
      }
      setError(parseErrorMessage(loadError, "Failed to load prompts."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void refreshPrompts(controller.signal);
    return () => controller.abort();
  }, [refreshPrompts]);

  const closeEditor = useCallback(() => {
    setIsEditorOpen(false);
    setSelectedPrompt(null);
    setFormError(null);
  }, []);

  const openCreateEditor = useCallback(() => {
    setEditorMode("create");
    setSelectedPrompt(null);
    setCommandName("");
    setDescription("");
    setPromptBody("");
    setFormError(null);
    setIsEditorOpen(true);
  }, []);

  const openEditEditor = useCallback(async (promptId: string) => {
    setEditorMode("edit");
    setSelectedPrompt(null);
    setCommandName("");
    setDescription("");
    setPromptBody("");
    setFormError(null);
    setIsEditorOpen(true);
    try {
      const detail = await getPrompt(promptId);
      const mapped = toPromptTemplate(detail);
      setSelectedPrompt(mapped);
      setCommandName(detail.name);
      setDescription(detail.description);
      setPromptBody(detail.prompt);
    } catch (loadError) {
      setFormError(
        parseErrorMessage(loadError, "Failed to load prompt details."),
      );
    }
  }, []);

  const normalizedCommandName = useMemo(
    () => normalizePromptCommandName(commandName),
    [commandName],
  );

  const submitEditor = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();

      const normalizedDescription = description.trim();
      const normalizedPromptBody = promptBody.trim();

      if (!normalizedCommandName) {
        setFormError("Prompt command name is required.");
        return;
      }
      if (!PROMPT_COMMAND_PATTERN.test(normalizedCommandName)) {
        setFormError(
          "Use 2-40 chars: lowercase letters, numbers, hyphen, or underscore.",
        );
        return;
      }
      if (!normalizedPromptBody) {
        setFormError("Prompt text is required.");
        return;
      }

      setIsSubmitting(true);
      setFormError(null);
      try {
        if (editorMode === "create") {
          const payload: PromptCreateInput = {
            name: normalizedCommandName,
            description: normalizedDescription,
            prompt: normalizedPromptBody,
          };
          await createPrompt(payload);
        } else {
          if (!selectedPrompt) {
            return;
          }

          const payload: PromptUpdateInput = {};
          if (normalizedCommandName !== selectedPrompt.name) {
            payload.name = normalizedCommandName;
          }
          if (normalizedDescription !== selectedPrompt.description) {
            payload.description = normalizedDescription;
          }
          if (normalizedPromptBody !== selectedPrompt.prompt) {
            payload.prompt = normalizedPromptBody;
          }

          if (Object.keys(payload).length > 0) {
            await updatePrompt(selectedPrompt.id, payload);
          }
        }

        await refreshPrompts();
        closeEditor();
      } catch (submitError) {
        setFormError(
          parseErrorMessage(
            submitError,
            editorMode === "create"
              ? "Failed to create prompt."
              : "Failed to save prompt.",
          ),
        );
      } finally {
        setIsSubmitting(false);
      }
    },
    [
      closeEditor,
      description,
      editorMode,
      normalizedCommandName,
      promptBody,
      refreshPrompts,
      selectedPrompt,
    ],
  );

  const removePrompt = useCallback(
    async (promptId: string) => {
      const target = prompts.find((item) => item.id === promptId);
      if (!target) {
        return;
      }
      const confirmed = window.confirm(
        `Delete \\${target.name}? This cannot be undone.`,
      );
      if (!confirmed) {
        return;
      }

      setDeletingPromptId(promptId);
      try {
        await deletePrompt(promptId);
        if (selectedPrompt?.id === promptId) {
          closeEditor();
        }
        await refreshPrompts();
      } catch (deleteError) {
        window.alert(
          parseErrorMessage(deleteError, "Failed to delete prompt."),
        );
      } finally {
        setDeletingPromptId(null);
      }
    },
    [closeEditor, prompts, refreshPrompts, selectedPrompt?.id],
  );

  return {
    prompts,
    isLoading,
    error,
    isEditorOpen,
    editorMode,
    expandedPromptId,
    selectedPrompt,
    commandName,
    description,
    promptBody,
    formError,
    isSubmitting,
    deletingPromptId,
    setCommandName,
    setDescription,
    setPromptBody,
    setExpandedPromptId,
    openCreateEditor,
    openEditEditor,
    closeEditor,
    submitEditor,
    deletePrompt: removePrompt,
  };
}
