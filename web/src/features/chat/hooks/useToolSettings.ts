import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getToolSettings,
  patchToolSettings,
} from "@/shared/api/clients/settings.client";
import type {
  ToolCatalogGroup,
  ToolCatalogTool,
  ToolSettingsResponse,
} from "@/shared/api/schemas/settings";

function parseErrorMessage(error: unknown, fallback: string) {
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
}

function withAppliedOverrides(
  current: ToolSettingsResponse,
  overrides: Record<string, boolean>,
): ToolSettingsResponse {
  const mergedOverrides = {
    ...current.tool_overrides,
    ...overrides,
  };

  const groups = current.groups.map((group) => {
    const tools = group.tools.map((tool) => {
      const nextEnabledSetting =
        mergedOverrides[tool.key] ?? tool.default_enabled;
      const enabled = tool.available ? nextEnabledSetting : false;
      return {
        ...tool,
        enabled,
      };
    });

    return {
      ...group,
      enabled: tools.some((tool) => tool.enabled),
      tools,
    };
  });

  return {
    ...current,
    groups,
    tool_overrides: mergedOverrides,
  };
}

function findGroup(settings: ToolSettingsResponse, groupKey: string) {
  return settings.groups.find((group) => group.key === groupKey) ?? null;
}

function findTool(settings: ToolSettingsResponse, toolKey: string) {
  for (const group of settings.groups) {
    const tool = group.tools.find((item) => item.key === toolKey);
    if (tool) {
      return tool;
    }
  }
  return null;
}

function mapsEqual(
  left: Record<string, boolean>,
  right: Record<string, boolean>,
) {
  const keys = new Set([...Object.keys(left), ...Object.keys(right)]);
  for (const key of keys) {
    if (left[key] !== right[key]) {
      return false;
    }
  }
  return true;
}

export function useToolSettings() {
  const [settings, setSettings] = useState<ToolSettingsResponse | null>(null);
  const [draftOverrides, setDraftOverrides] = useState<Record<string, boolean>>(
    {},
  );
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const reload = useCallback(async (signal?: AbortSignal) => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const payload = await getToolSettings(signal);
      setSettings(payload);
      setDraftOverrides(payload.tool_overrides);
      setSaveError(null);
    } catch (error) {
      if (signal?.aborted) {
        return;
      }
      setLoadError(parseErrorMessage(error, "Failed to load tool settings."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void reload(controller.signal);
    return () => controller.abort();
  }, [reload]);

  const effectiveSettings = useMemo(() => {
    if (!settings) {
      return null;
    }
    return withAppliedOverrides(settings, draftOverrides);
  }, [settings, draftOverrides]);

  const hasUnsavedChanges = useMemo(() => {
    if (!settings) {
      return false;
    }
    return !mapsEqual(draftOverrides, settings.tool_overrides);
  }, [draftOverrides, settings]);

  const toggleTool = useCallback((toolKey: string, enabled: boolean) => {
    setDraftOverrides((prev) => ({
      ...prev,
      [toolKey]: enabled,
    }));
  }, []);

  const toggleGroup = useCallback(
    (groupKey: string, enabled: boolean) => {
      if (!settings) {
        return;
      }

      setDraftOverrides((prev) => {
        const resolved = withAppliedOverrides(settings, prev);
        const group = findGroup(resolved, groupKey);
        if (!group) {
          return prev;
        }

        const next = { ...prev };
        for (const tool of group.tools) {
          if (enabled) {
            if (tool.available) {
              next[tool.key] = true;
            }
          } else {
            next[tool.key] = false;
          }
        }
        return next;
      });
    },
    [settings],
  );

  const save = useCallback(async () => {
    if (!settings || !hasUnsavedChanges || isSaving) {
      return false;
    }

    setSaveError(null);
    setIsSaving(true);
    try {
      const next = await patchToolSettings({ tool_overrides: draftOverrides });
      setSettings(next);
      setDraftOverrides(next.tool_overrides);
      return true;
    } catch (error) {
      setSaveError(parseErrorMessage(error, "Failed to save tool settings."));
      return false;
    } finally {
      setIsSaving(false);
    }
  }, [draftOverrides, hasUnsavedChanges, isSaving, settings]);

  const discardChanges = useCallback(() => {
    if (!settings) {
      return;
    }
    setDraftOverrides(settings.tool_overrides);
    setSaveError(null);
  }, [settings]);

  const groups = useMemo<ToolCatalogGroup[]>(
    () => effectiveSettings?.groups ?? [],
    [effectiveSettings],
  );

  const getTool = useCallback(
    (toolKey: string): ToolCatalogTool | null => {
      if (!effectiveSettings) {
        return null;
      }
      return findTool(effectiveSettings, toolKey);
    },
    [effectiveSettings],
  );

  return {
    settings,
    groups,
    isLoading,
    isSaving,
    loadError,
    saveError,
    hasUnsavedChanges,
    reload,
    toggleTool,
    toggleGroup,
    save,
    discardChanges,
    getTool,
  };
}
