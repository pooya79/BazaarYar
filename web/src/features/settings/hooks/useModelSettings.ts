import { useCallback, useEffect, useMemo, useState } from "react";
import {
  activateModelCard,
  createModelCard,
  deleteModelCard,
  getModelCards,
  patchModelCard,
  setDefaultModelCard,
} from "@/shared/api/clients/settings.client";
import type {
  ModelCard,
  ModelCardPatchInput,
  ModelCardsResponse,
} from "@/shared/api/schemas/settings";
import {
  emptyModelCardDraft,
  type ModelCardDraft,
  toModelCardDraft,
} from "../model/types";

const parseErrorMessage = (error: unknown, fallback: string) => {
  if (error && typeof error === "object" && "message" in error) {
    const message = (error as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return fallback;
};

const dispatchModelCardsRefresh = () => {
  window.dispatchEvent(new Event("model-cards:refresh"));
};

function toDraftMap(items: ModelCard[]): Record<string, ModelCardDraft> {
  return Object.fromEntries(
    items.map((card) => [card.id, toModelCardDraft(card)]),
  );
}

function parseTemperature(value: string): number | null {
  const parsed = Number.parseFloat(value);
  if (Number.isNaN(parsed) || parsed < 0 || parsed > 2) {
    return null;
  }
  return parsed;
}

export function useModelSettings() {
  const [response, setResponse] = useState<ModelCardsResponse | null>(null);
  const [drafts, setDrafts] = useState<Record<string, ModelCardDraft>>({});
  const [newCardDraft, setNewCardDraft] = useState<ModelCardDraft>({
    ...emptyModelCardDraft,
    displayName: "New model",
    modelName: "gpt-4.1-mini",
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const applyResponse = useCallback((next: ModelCardsResponse) => {
    setResponse(next);
    setDrafts(toDraftMap(next.items));
  }, []);

  const reload = useCallback(
    async (signal?: AbortSignal) => {
      setIsLoading(true);
      setLoadError(null);
      try {
        const payload = await getModelCards(signal);
        applyResponse(payload);
      } catch (error) {
        if (signal?.aborted) {
          return;
        }
        setLoadError(parseErrorMessage(error, "Failed to load model cards."));
      } finally {
        setIsLoading(false);
      }
    },
    [applyResponse],
  );

  useEffect(() => {
    const controller = new AbortController();
    void reload(controller.signal);
    return () => controller.abort();
  }, [reload]);

  const cards = response?.items ?? [];
  const activeModelId = response?.active_model_id ?? null;
  const defaultModelId = response?.default_model_id ?? null;

  const cardsById = useMemo(
    () => Object.fromEntries(cards.map((card) => [card.id, card])),
    [cards],
  );

  const updateDraft = useCallback(
    <K extends keyof ModelCardDraft>(
      modelId: string,
      key: K,
      value: ModelCardDraft[K],
    ) => {
      setDrafts((current) => ({
        ...current,
        [modelId]: {
          ...(current[modelId] ?? emptyModelCardDraft),
          [key]: value,
        },
      }));
    },
    [],
  );

  const setReplacementApiKey = useCallback((modelId: string, value: string) => {
    setDrafts((current) => {
      const existing = current[modelId] ?? emptyModelCardDraft;
      return {
        ...current,
        [modelId]: {
          ...existing,
          replacementApiKey: value,
          pendingClearKey: value.trim() ? false : existing.pendingClearKey,
        },
      };
    });
  }, []);

  const markClearApiKey = useCallback((modelId: string) => {
    setDrafts((current) => {
      const existing = current[modelId] ?? emptyModelCardDraft;
      return {
        ...current,
        [modelId]: {
          ...existing,
          replacementApiKey: "",
          pendingClearKey: true,
        },
      };
    });
  }, []);

  const cancelClearApiKey = useCallback((modelId: string) => {
    setDrafts((current) => {
      const existing = current[modelId] ?? emptyModelCardDraft;
      return {
        ...current,
        [modelId]: {
          ...existing,
          pendingClearKey: false,
        },
      };
    });
  }, []);

  const runMutation = useCallback(
    async (
      action: () => Promise<ModelCardsResponse>,
      successMessage: string,
      fallbackError: string,
    ) => {
      setActionError(null);
      setActionSuccess(null);
      setIsWorking(true);
      try {
        const next = await action();
        applyResponse(next);
        setActionSuccess(successMessage);
        dispatchModelCardsRefresh();
        return true;
      } catch (error) {
        setActionError(parseErrorMessage(error, fallbackError));
        return false;
      } finally {
        setIsWorking(false);
      }
    },
    [applyResponse],
  );

  const saveCard = useCallback(
    async (modelId: string) => {
      const card = cardsById[modelId];
      const draft = drafts[modelId];
      if (!card || !draft) {
        return false;
      }

      const payload: ModelCardPatchInput = {};
      const displayName = draft.displayName.trim();
      const modelName = draft.modelName.trim();
      const baseUrl = draft.baseUrl.trim();
      const temperature = parseTemperature(draft.temperature);

      if (!displayName) {
        setActionError("Display name is required.");
        return false;
      }
      if (!modelName) {
        setActionError("Model name is required.");
        return false;
      }
      if (temperature === null) {
        setActionError("Temperature must be a number between 0 and 2.");
        return false;
      }

      if (displayName !== card.display_name) {
        payload.display_name = displayName;
      }
      if (modelName !== card.model_name) {
        payload.model_name = modelName;
      }
      if (baseUrl !== card.base_url) {
        payload.base_url = baseUrl;
      }
      if (temperature !== card.temperature) {
        payload.temperature = temperature;
      }
      if (draft.reasoningEffort !== card.reasoning_effort) {
        payload.reasoning_effort = draft.reasoningEffort;
      }
      if (draft.reasoningEnabled !== card.reasoning_enabled) {
        payload.reasoning_enabled = draft.reasoningEnabled;
      }
      if (draft.pendingClearKey) {
        payload.api_key = "";
      } else if (draft.replacementApiKey.trim()) {
        payload.api_key = draft.replacementApiKey.trim();
      }

      if (Object.keys(payload).length === 0) {
        setActionSuccess("No changes to save.");
        return true;
      }

      return runMutation(
        () => patchModelCard(modelId, payload),
        "Model card saved.",
        "Failed to save model card.",
      );
    },
    [cardsById, drafts, runMutation],
  );

  const createCard = useCallback(async () => {
    const displayName = newCardDraft.displayName.trim();
    const modelName = newCardDraft.modelName.trim();
    const baseUrl = newCardDraft.baseUrl.trim();
    const temperature = parseTemperature(newCardDraft.temperature);

    if (!displayName) {
      setActionError("Display name is required.");
      return false;
    }
    if (!modelName) {
      setActionError("Model name is required.");
      return false;
    }
    if (temperature === null) {
      setActionError("Temperature must be a number between 0 and 2.");
      return false;
    }

    const payload = {
      display_name: displayName,
      model_name: modelName,
      base_url: baseUrl,
      temperature,
      reasoning_effort: newCardDraft.reasoningEffort,
      reasoning_enabled: newCardDraft.reasoningEnabled,
      api_key: newCardDraft.replacementApiKey.trim() || undefined,
    };

    const ok = await runMutation(
      () => createModelCard(payload),
      "Model card created.",
      "Failed to create model card.",
    );
    if (!ok) {
      return false;
    }

    setNewCardDraft({
      ...emptyModelCardDraft,
      displayName: "New model",
      modelName: "gpt-4.1-mini",
    });
    return true;
  }, [newCardDraft, runMutation]);

  const deleteCard = useCallback(
    async (modelId: string) => {
      return runMutation(
        () => deleteModelCard(modelId),
        "Model card deleted.",
        "Failed to delete model card.",
      );
    },
    [runMutation],
  );

  const activateCard = useCallback(
    async (modelId: string) => {
      return runMutation(
        () => activateModelCard(modelId),
        "Active model updated.",
        "Failed to activate model card.",
      );
    },
    [runMutation],
  );

  const makeDefaultCard = useCallback(
    async (modelId: string) => {
      return runMutation(
        () => setDefaultModelCard(modelId),
        "Default model updated.",
        "Failed to set default model card.",
      );
    },
    [runMutation],
  );

  return {
    cards,
    drafts,
    newCardDraft,
    activeModelId,
    defaultModelId,
    isLoading,
    isWorking,
    loadError,
    actionError,
    actionSuccess,
    reload,
    updateDraft,
    setReplacementApiKey,
    markClearApiKey,
    cancelClearApiKey,
    setNewCardDraft,
    saveCard,
    createCard,
    deleteCard,
    activateCard,
    makeDefaultCard,
  };
}
