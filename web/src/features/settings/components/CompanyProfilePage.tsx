"use client";

import { RefreshCcw, Save, Trash2 } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { useCompanyProfile } from "../hooks/useCompanyProfile";

const panelClass =
  "rounded-2xl border border-marketing-border bg-marketing-surface p-5 shadow-marketing-subtle";
const fieldClass =
  "h-9 w-full rounded-lg border border-marketing-border bg-marketing-surface px-3 text-sm text-marketing-text-primary outline-none transition-colors focus:border-marketing-primary";
const textareaClass =
  "min-h-[130px] w-full rounded-lg border border-marketing-border bg-marketing-surface px-3 py-2 text-sm text-marketing-text-primary outline-none transition-colors focus:border-marketing-primary";

export function CompanyProfilePage() {
  const {
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
  } = useCompanyProfile();

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="rounded-2xl border border-marketing-border bg-marketing-surface px-6 py-4 text-sm text-marketing-text-secondary shadow-marketing-subtle">
          Loading company profile...
        </div>
      </div>
    );
  }

  if (loadError || !profile) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="w-full max-w-lg rounded-2xl border border-marketing-border bg-marketing-surface p-6 shadow-marketing-subtle">
          <h2 className="text-lg font-semibold text-marketing-text-primary">
            Unable to load company profile
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
    profile.source === "database" ? "Database override" : "Default values";
  const sourceClass =
    profile.source === "database"
      ? "border-marketing-primary/30 bg-marketing-accent-soft text-marketing-primary"
      : "border-marketing-border bg-marketing-accent-soft text-marketing-text-secondary";

  return (
    <div className="flex flex-1 flex-col overflow-y-auto p-4 md:p-8">
      <div className="mx-auto flex w-full max-w-[920px] flex-col gap-5">
        <div className={panelClass}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold text-marketing-text-primary">
                Company Profile
              </h2>
              <p className="mt-1 text-sm text-marketing-text-secondary">
                Set company context the assistant should use in its system
                prompt.
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
          <label className="flex items-center gap-2 text-sm text-marketing-text-secondary">
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(event) => updateDraft("enabled", event.target.checked)}
              className="size-4 rounded border-marketing-border"
            />
            Enable company context
          </label>

          {!draft.enabled ? (
            <div className="rounded-lg border border-marketing-border bg-marketing-accent-soft px-3 py-2 text-sm text-marketing-text-secondary">
              Company context is disabled. Name and description are saved but
              not injected into the system prompt.
            </div>
          ) : null}

          <div className="space-y-1">
            <label
              htmlFor="company-name"
              className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted"
            >
              Company name
            </label>
            <input
              id="company-name"
              className={fieldClass}
              value={draft.name}
              maxLength={255}
              onChange={(event) => updateDraft("name", event.target.value)}
              placeholder="Acme Inc."
            />
          </div>

          <div className="space-y-1">
            <label
              htmlFor="company-description"
              className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted"
            >
              Company description
            </label>
            <textarea
              id="company-description"
              className={textareaClass}
              value={draft.description}
              onChange={(event) =>
                updateDraft("description", event.target.value)
              }
              placeholder="What your company does, target market, and brand context for marketing responses."
            />
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
                  "Reset company profile to defaults?",
                );
                if (!confirmed) {
                  return;
                }
                void reset();
              }}
            >
              <Trash2 className="size-4" aria-hidden="true" />
              {isResetting ? "Resetting..." : "Reset to defaults"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
