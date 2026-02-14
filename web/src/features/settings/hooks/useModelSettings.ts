import { useCallback, useEffect, useState } from "react";
import {
  getModelSettings,
  patchModelSettings,
  resetModelSettings,
} from "@/shared/api/clients/settings.client";
import type {
  ModelSettingsPatchInput,
  ModelSettingsResponse,
} from "@/shared/api/schemas/settings";
import {
  emptySettingsDraft,
  type ModelSettingsDraft,
  toSettingsDraft,
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

export function useModelSettings() {
  const [settings, setSettings] = useState<ModelSettingsResponse | null>(null);
  const [draft, setDraft] = useState<ModelSettingsDraft>(emptySettingsDraft);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const applySettings = useCallback((nextSettings: ModelSettingsResponse) => {
    setSettings(nextSettings);
    setDraft(toSettingsDraft(nextSettings));
  }, []);

  const reload = useCallback(
    async (signal?: AbortSignal) => {
      setIsLoading(true);
      setLoadError(null);
      try {
        const nextSettings = await getModelSettings(signal);
        applySettings(nextSettings);
      } catch (error) {
        if (signal?.aborted) {
          return;
        }
        setLoadError(
          parseErrorMessage(error, "Failed to load model settings."),
        );
      } finally {
        setIsLoading(false);
      }
    },
    [applySettings],
  );

  useEffect(() => {
    const controller = new AbortController();
    void reload(controller.signal);
    return () => controller.abort();
  }, [reload]);

  const updateDraft = useCallback(
    <K extends keyof ModelSettingsDraft>(
      key: K,
      value: ModelSettingsDraft[K],
    ) => {
      setDraft((current) => ({
        ...current,
        [key]: value,
      }));
    },
    [],
  );

  const setReplacementApiKey = useCallback((value: string) => {
    setDraft((current) => ({
      ...current,
      replacementApiKey: value,
      pendingClearKey: value.trim() ? false : current.pendingClearKey,
    }));
  }, []);

  const markClearApiKey = useCallback(() => {
    setDraft((current) => ({
      ...current,
      replacementApiKey: "",
      pendingClearKey: true,
    }));
  }, []);

  const cancelClearApiKey = useCallback(() => {
    setDraft((current) => ({
      ...current,
      pendingClearKey: false,
    }));
  }, []);

  const save = useCallback(async () => {
    if (!settings) {
      return false;
    }

    setSaveError(null);
    setSaveSuccess(null);

    const payload: ModelSettingsPatchInput = {};
    const normalizedModelName = draft.modelName.trim();
    const normalizedBaseUrl = draft.baseUrl.trim();
    const parsedTemperature = Number.parseFloat(draft.temperature);

    if (!normalizedModelName) {
      setSaveError("Model name is required.");
      return false;
    }
    if (
      Number.isNaN(parsedTemperature) ||
      parsedTemperature < 0 ||
      parsedTemperature > 2
    ) {
      setSaveError("Temperature must be a number between 0 and 2.");
      return false;
    }

    if (normalizedModelName !== settings.model_name) {
      payload.model_name = normalizedModelName;
    }
    if (normalizedBaseUrl !== settings.base_url) {
      payload.base_url = normalizedBaseUrl;
    }
    if (parsedTemperature !== settings.temperature) {
      payload.temperature = parsedTemperature;
    }
    if (draft.reasoningEffort !== settings.reasoning_effort) {
      payload.reasoning_effort = draft.reasoningEffort;
    }
    if (draft.reasoningEnabled !== settings.reasoning_enabled) {
      payload.reasoning_enabled = draft.reasoningEnabled;
    }
    if (draft.pendingClearKey) {
      payload.api_key = "";
    } else if (draft.replacementApiKey.trim()) {
      payload.api_key = draft.replacementApiKey.trim();
    }

    if (Object.keys(payload).length === 0) {
      setSaveSuccess("No changes to save.");
      return true;
    }

    setIsSaving(true);
    try {
      const nextSettings = await patchModelSettings(payload);
      applySettings(nextSettings);
      setSaveSuccess("Settings saved.");
      return true;
    } catch (error) {
      setSaveError(parseErrorMessage(error, "Failed to save model settings."));
      return false;
    } finally {
      setIsSaving(false);
    }
  }, [applySettings, draft, settings]);

  const reset = useCallback(async () => {
    setSaveError(null);
    setSaveSuccess(null);
    setIsResetting(true);
    try {
      await resetModelSettings();
      const nextSettings = await getModelSettings();
      applySettings(nextSettings);
      setSaveSuccess("Settings reset to environment defaults.");
      return true;
    } catch (error) {
      setSaveError(parseErrorMessage(error, "Failed to reset model settings."));
      return false;
    } finally {
      setIsResetting(false);
    }
  }, [applySettings]);

  return {
    settings,
    draft,
    isLoading,
    isSaving,
    isResetting,
    loadError,
    saveError,
    saveSuccess,
    reload,
    save,
    reset,
    updateDraft,
    setReplacementApiKey,
    markClearApiKey,
    cancelClearApiKey,
  };
}
