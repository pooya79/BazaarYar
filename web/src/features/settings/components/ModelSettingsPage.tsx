"use client";

import { RefreshCcw, Save, Trash2 } from "lucide-react";
import { Button } from "@/shared/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/ui/select";
import { useModelSettings } from "../hooks/useModelSettings";

const panelClass =
  "rounded-2xl border border-marketing-border bg-marketing-surface p-5 shadow-marketing-subtle";
const fieldClass =
  "h-9 w-full rounded-lg border border-marketing-border bg-marketing-surface px-3 text-sm text-marketing-text-primary outline-none transition-colors focus:border-marketing-primary";

export function ModelSettingsPage() {
  const {
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
  } = useModelSettings();

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="rounded-2xl border border-marketing-border bg-marketing-surface px-6 py-4 text-sm text-marketing-text-secondary shadow-marketing-subtle">
          Loading model settings...
        </div>
      </div>
    );
  }

  if (loadError || !settings) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="w-full max-w-lg rounded-2xl border border-marketing-border bg-marketing-surface p-6 shadow-marketing-subtle">
          <h2 className="text-lg font-semibold text-marketing-text-primary">
            Unable to load model settings
          </h2>
          <p className="mt-2 text-sm text-marketing-text-secondary">
            {loadError ?? "Unknown error."}
          </p>
          <Button
            type="button"
            className="mt-4"
            onClick={() => {
              void reload();
            }}
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  const sourceLabel =
    settings.source === "database"
      ? "Database override"
      : "Environment defaults";
  const sourceClass =
    settings.source === "database"
      ? "border-marketing-primary/30 bg-marketing-accent-soft text-marketing-primary"
      : "border-marketing-border bg-marketing-accent-soft text-marketing-text-secondary";

  return (
    <div className="flex flex-1 flex-col overflow-y-auto p-4 md:p-8">
      <div className="mx-auto flex w-full max-w-[920px] flex-col gap-5">
        <div className={panelClass}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold text-marketing-text-primary">
                Model Settings
              </h2>
              <p className="mt-1 text-sm text-marketing-text-secondary">
                Configure the model backend used by the assistant.
              </p>
            </div>
            <span
              className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.08em] ${sourceClass}`}
            >
              {sourceLabel}
            </span>
          </div>
        </div>

        <form
          className={`${panelClass} space-y-4`}
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1">
              <label
                htmlFor="model-name"
                className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted"
              >
                Model name
              </label>
              <input
                id="model-name"
                className={fieldClass}
                value={draft.modelName}
                onChange={(event) =>
                  updateDraft("modelName", event.target.value)
                }
                placeholder="gpt-4.1-mini"
              />
            </div>

            <div className="space-y-1">
              <label
                htmlFor="base-url"
                className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted"
              >
                Base URL
              </label>
              <input
                id="base-url"
                className={fieldClass}
                value={draft.baseUrl}
                onChange={(event) => updateDraft("baseUrl", event.target.value)}
                placeholder="https://openrouter.ai/api/v1"
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1">
              <label
                htmlFor="temperature"
                className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted"
              >
                Temperature (0 - 2)
              </label>
              <input
                id="temperature"
                type="number"
                min={0}
                max={2}
                step={0.1}
                className={fieldClass}
                value={draft.temperature}
                onChange={(event) =>
                  updateDraft("temperature", event.target.value)
                }
              />
            </div>

            <div className="space-y-1">
              <p className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
                Reasoning effort
              </p>
              <Select
                value={draft.reasoningEffort}
                onValueChange={(value) =>
                  updateDraft(
                    "reasoningEffort",
                    value as "low" | "medium" | "high",
                  )
                }
              >
                <SelectTrigger className="h-9 w-full border-marketing-border bg-marketing-surface">
                  <SelectValue placeholder="Effort" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <label className="flex items-center gap-2 text-sm text-marketing-text-secondary">
            <input
              type="checkbox"
              checked={draft.reasoningEnabled}
              onChange={(event) =>
                updateDraft("reasoningEnabled", event.target.checked)
              }
              className="size-4 rounded border-marketing-border"
            />
            Enable reasoning
          </label>

          <div className="space-y-2 rounded-xl border border-marketing-border bg-marketing-accent-soft p-3">
            <div className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
              API key
            </div>
            <p className="text-sm text-marketing-text-secondary">
              Current key:{" "}
              {settings.has_api_key
                ? settings.api_key_preview || "[masked]"
                : "Not configured"}
            </p>
            <input
              type="password"
              className={fieldClass}
              value={draft.replacementApiKey}
              onChange={(event) => setReplacementApiKey(event.target.value)}
              placeholder="Leave empty to keep current key"
            />
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                className="border-marketing-border"
                onClick={markClearApiKey}
                disabled={!settings.has_api_key && !draft.pendingClearKey}
              >
                Clear key on save
              </Button>
              {draft.pendingClearKey ? (
                <Button
                  type="button"
                  variant="outline"
                  className="border-marketing-border"
                  onClick={cancelClearApiKey}
                >
                  Undo clear
                </Button>
              ) : null}
            </div>
            {draft.pendingClearKey ? (
              <p className="text-sm text-marketing-danger">
                API key will be cleared when you save.
              </p>
            ) : null}
          </div>

          {saveError ? (
            <div className="rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
              {saveError}
            </div>
          ) : null}

          {saveSuccess ? (
            <div className="rounded-lg border border-marketing-primary/30 bg-marketing-accent-soft px-3 py-2 text-sm text-marketing-primary">
              {saveSuccess}
            </div>
          ) : null}

          <div className="flex flex-wrap gap-2 pt-1">
            <Button
              type="submit"
              disabled={isSaving || isResetting}
              className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
            >
              <Save className="size-4" aria-hidden="true" />
              {isSaving ? "Saving..." : "Save changes"}
            </Button>
            <Button
              type="button"
              variant="outline"
              className="border-marketing-border"
              disabled={isSaving || isResetting}
              onClick={() => {
                void reload();
              }}
            >
              <RefreshCcw className="size-4" aria-hidden="true" />
              Reload
            </Button>
            <Button
              type="button"
              variant="outline"
              className="border-marketing-danger text-marketing-danger hover:bg-marketing-danger-soft hover:text-marketing-danger"
              disabled={isSaving || isResetting}
              onClick={() => {
                const confirmed = window.confirm(
                  "Reset model settings to environment defaults?",
                );
                if (!confirmed) {
                  return;
                }
                void reset();
              }}
            >
              <Trash2 className="size-4" aria-hidden="true" />
              {isResetting ? "Resetting..." : "Reset to env defaults"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
