import { useCallback, useEffect, useState } from "react";
import {
  getCompanyProfile,
  patchCompanyProfile,
  resetCompanyProfile,
} from "@/shared/api/clients/settings.client";
import type {
  CompanyProfilePatchInput,
  CompanyProfileResponse,
} from "@/shared/api/schemas/settings";
import {
  type CompanyProfileDraft,
  emptyCompanyProfileDraft,
  toCompanyProfileDraft,
} from "../model/companyTypes";

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

export function useCompanyProfile() {
  const [profile, setProfile] = useState<CompanyProfileResponse | null>(null);
  const [draft, setDraft] = useState<CompanyProfileDraft>(
    emptyCompanyProfileDraft,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const applyProfile = useCallback((nextProfile: CompanyProfileResponse) => {
    setProfile(nextProfile);
    setDraft(toCompanyProfileDraft(nextProfile));
  }, []);

  const reload = useCallback(
    async (signal?: AbortSignal) => {
      setIsLoading(true);
      setLoadError(null);
      try {
        const nextProfile = await getCompanyProfile(signal);
        applyProfile(nextProfile);
      } catch (error) {
        if (signal?.aborted) {
          return;
        }
        setLoadError(
          parseErrorMessage(error, "Failed to load company profile."),
        );
      } finally {
        setIsLoading(false);
      }
    },
    [applyProfile],
  );

  useEffect(() => {
    const controller = new AbortController();
    void reload(controller.signal);
    return () => controller.abort();
  }, [reload]);

  const updateDraft = useCallback(
    <K extends keyof CompanyProfileDraft>(
      key: K,
      value: CompanyProfileDraft[K],
    ) => {
      setDraft((current) => ({
        ...current,
        [key]: value,
      }));
    },
    [],
  );

  const save = useCallback(async () => {
    if (!profile) {
      return false;
    }

    setSaveError(null);
    setSaveSuccess(null);

    const payload: CompanyProfilePatchInput = {};
    const normalizedName = draft.name.trim();
    const normalizedDescription = draft.description.trim();
    if (normalizedName.length > 255) {
      setSaveError("Company name must be 255 characters or fewer.");
      return false;
    }

    if (draft.enabled !== profile.enabled) {
      payload.enabled = draft.enabled;
    }
    if (normalizedName !== profile.name) {
      payload.name = normalizedName;
    }
    if (normalizedDescription !== profile.description) {
      payload.description = normalizedDescription;
    }

    if (Object.keys(payload).length === 0) {
      setSaveSuccess("No changes to save.");
      return true;
    }

    setIsSaving(true);
    try {
      const nextProfile = await patchCompanyProfile(payload);
      applyProfile(nextProfile);
      setSaveSuccess("Company profile saved.");
      return true;
    } catch (error) {
      setSaveError(parseErrorMessage(error, "Failed to save company profile."));
      return false;
    } finally {
      setIsSaving(false);
    }
  }, [applyProfile, draft, profile]);

  const reset = useCallback(async () => {
    setSaveError(null);
    setSaveSuccess(null);
    setIsResetting(true);
    try {
      await resetCompanyProfile();
      const nextProfile = await getCompanyProfile();
      applyProfile(nextProfile);
      setSaveSuccess("Company profile reset to defaults.");
      return true;
    } catch (error) {
      setSaveError(
        parseErrorMessage(error, "Failed to reset company profile."),
      );
      return false;
    } finally {
      setIsResetting(false);
    }
  }, [applyProfile]);

  return {
    profile,
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
  };
}
