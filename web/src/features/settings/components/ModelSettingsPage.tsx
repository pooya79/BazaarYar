"use client";

import * as Dialog from "@radix-ui/react-dialog";
import {
  MoreHorizontal,
  Plus,
  RefreshCcw,
  Save,
  Trash2,
  X,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/shared/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
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
const labelClass =
  "text-[11px] font-semibold uppercase tracking-[0.08em] text-marketing-text-muted";

const defaultCreateDraft = {
  displayName: "New model",
  modelName: "gpt-4.1-mini",
  baseUrl: "",
  temperature: "1",
  reasoningEffort: "medium" as const,
  reasoningEnabled: true,
  replacementApiKey: "",
  pendingClearKey: false,
};

export function ModelSettingsPage() {
  const {
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
  } = useModelSettings();

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editingModelId, setEditingModelId] = useState<string | null>(null);

  const editingCard = useMemo(
    () => cards.find((item) => item.id === editingModelId) ?? null,
    [cards, editingModelId],
  );
  const editingDraft = editingModelId ? drafts[editingModelId] : null;

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="rounded-2xl border border-marketing-border bg-marketing-surface px-6 py-4 text-sm text-marketing-text-secondary shadow-marketing-subtle">
          Loading model cards...
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="w-full max-w-lg rounded-2xl border border-marketing-border bg-marketing-surface p-6 shadow-marketing-subtle">
          <h2 className="text-lg font-semibold text-marketing-text-primary">
            Unable to load model cards
          </h2>
          <p className="mt-2 text-sm text-marketing-text-secondary">
            {loadError}
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

  return (
    <div className="flex flex-1 flex-col overflow-y-auto p-4 md:p-8">
      <div className="mx-auto flex w-full max-w-[980px] flex-col gap-5">
        <div className={panelClass}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold text-marketing-text-primary">
                Model Cards
              </h2>
              <p className="mt-1 text-sm text-marketing-text-secondary">
                Compact model list with quick actions.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="rounded-full border border-marketing-border bg-marketing-accent-soft px-3 py-1 text-xs text-marketing-text-secondary">
                {cards.length} card{cards.length === 1 ? "" : "s"}
              </span>
              <Button
                type="button"
                variant="outline"
                className="border-marketing-border"
                onClick={() => {
                  void reload();
                }}
                disabled={isWorking}
              >
                <RefreshCcw className="size-4" aria-hidden="true" />
                Reload
              </Button>
              <Button
                type="button"
                className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
                onClick={() => {
                  setNewCardDraft(defaultCreateDraft);
                  setCreateModalOpen(true);
                }}
                disabled={isWorking}
              >
                <Plus className="size-4" aria-hidden="true" />
                Add model
              </Button>
            </div>
          </div>
        </div>

        <div className="overflow-hidden rounded-2xl border border-marketing-border bg-marketing-surface shadow-marketing-subtle">
          {cards.map((card, index) => {
            const isActive = card.id === activeModelId;
            const isDefault = card.id === defaultModelId;

            return (
              <div
                key={card.id}
                className={`flex items-center justify-between gap-3 px-4 py-3 ${
                  index === cards.length - 1
                    ? ""
                    : "border-b border-marketing-border"
                }`}
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-marketing-text-primary">
                    {card.display_name}
                  </p>
                  <p className="truncate text-xs text-marketing-text-secondary">
                    {card.model_name}
                    {card.base_url ? ` • ${card.base_url}` : ""}
                  </p>
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  <span
                    className={`rounded-full border px-2 py-1 text-xs ${
                      isActive
                        ? "border-marketing-primary/30 bg-marketing-accent-soft text-marketing-primary"
                        : "border-marketing-border text-marketing-text-secondary"
                    }`}
                  >
                    {isActive ? "Active" : "Inactive"}
                  </span>
                  <span
                    className={`rounded-full border px-2 py-1 text-xs ${
                      isDefault
                        ? "border-marketing-primary/30 bg-marketing-accent-soft text-marketing-primary"
                        : "border-marketing-border text-marketing-text-secondary"
                    }`}
                  >
                    {isDefault ? "Default" : "Standard"}
                  </span>

                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        className="h-8 w-8 border-marketing-border"
                        aria-label="Model actions"
                      >
                        <MoreHorizontal className="size-4" aria-hidden="true" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      align="end"
                      className="border-marketing-border"
                    >
                      <DropdownMenuItem
                        onSelect={() => {
                          setEditingModelId(card.id);
                        }}
                      >
                        Edit
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        disabled={isActive || isWorking}
                        onSelect={() => {
                          void activateCard(card.id);
                        }}
                      >
                        Set as active
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        disabled={isDefault || isWorking}
                        onSelect={() => {
                          void makeDefaultCard(card.id);
                        }}
                      >
                        Set as default
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        className="text-marketing-danger focus:text-marketing-danger"
                        disabled={cards.length <= 1 || isWorking}
                        onSelect={() => {
                          const confirmed = window.confirm(
                            `Delete model card "${card.display_name}"?`,
                          );
                          if (!confirmed) {
                            return;
                          }
                          void deleteCard(card.id);
                        }}
                      >
                        <Trash2 className="size-4" aria-hidden="true" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            );
          })}
        </div>

        {actionError ? (
          <div className="rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
            {actionError}
          </div>
        ) : null}

        {actionSuccess ? (
          <div className="rounded-lg border border-marketing-primary/30 bg-marketing-accent-soft px-3 py-2 text-sm text-marketing-primary">
            {actionSuccess}
          </div>
        ) : null}
      </div>

      <Dialog.Root open={createModalOpen} onOpenChange={setCreateModalOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-[140] bg-black/60 backdrop-blur-[1px]" />
          <Dialog.Content className="fixed top-1/2 left-1/2 z-[150] flex w-[min(94vw,36rem)] -translate-x-1/2 -translate-y-1/2 flex-col rounded-2xl border border-marketing-border bg-marketing-surface shadow-marketing-glow">
            <div className="flex items-start justify-between border-b border-marketing-border px-5 py-4">
              <div>
                <Dialog.Title className="text-lg font-semibold text-marketing-text-primary">
                  Create Model Card
                </Dialog.Title>
                <Dialog.Description className="mt-1 text-sm text-marketing-text-secondary">
                  Add a new model preset to use in chat selection.
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 rounded-md text-marketing-text-muted hover:bg-marketing-accent-medium hover:text-marketing-text-primary"
                >
                  <X className="size-4" aria-hidden="true" />
                </Button>
              </Dialog.Close>
            </div>

            <form
              className="space-y-4 px-5 py-4"
              onSubmit={(event) => {
                event.preventDefault();
                void (async () => {
                  const ok = await createCard();
                  if (ok) {
                    setCreateModalOpen(false);
                  }
                })();
              }}
            >
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <label className={labelClass} htmlFor="new-display-name">
                    Display name
                  </label>
                  <input
                    id="new-display-name"
                    className={`${fieldClass} mt-1`}
                    value={newCardDraft.displayName}
                    onChange={(event) =>
                      setNewCardDraft((current) => ({
                        ...current,
                        displayName: event.target.value,
                      }))
                    }
                    placeholder="Primary model"
                  />
                </div>
                <div>
                  <label className={labelClass} htmlFor="new-model-name">
                    Model name
                  </label>
                  <input
                    id="new-model-name"
                    className={`${fieldClass} mt-1`}
                    value={newCardDraft.modelName}
                    onChange={(event) =>
                      setNewCardDraft((current) => ({
                        ...current,
                        modelName: event.target.value,
                      }))
                    }
                    placeholder="gpt-4.1-mini"
                  />
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <label className={labelClass} htmlFor="new-base-url">
                    Base URL
                  </label>
                  <input
                    id="new-base-url"
                    className={`${fieldClass} mt-1`}
                    value={newCardDraft.baseUrl}
                    onChange={(event) =>
                      setNewCardDraft((current) => ({
                        ...current,
                        baseUrl: event.target.value,
                      }))
                    }
                    placeholder="https://openrouter.ai/api/v1"
                  />
                </div>
                <div>
                  <label className={labelClass} htmlFor="new-api-key">
                    API key (optional)
                  </label>
                  <input
                    id="new-api-key"
                    type="password"
                    className={`${fieldClass} mt-1`}
                    value={newCardDraft.replacementApiKey}
                    onChange={(event) =>
                      setNewCardDraft((current) => ({
                        ...current,
                        replacementApiKey: event.target.value,
                      }))
                    }
                    placeholder="sk-..."
                  />
                </div>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <div>
                  <label className={labelClass} htmlFor="new-temperature">
                    Temperature
                  </label>
                  <input
                    id="new-temperature"
                    type="number"
                    min={0}
                    max={2}
                    step={0.1}
                    className={`${fieldClass} mt-1`}
                    value={newCardDraft.temperature}
                    onChange={(event) =>
                      setNewCardDraft((current) => ({
                        ...current,
                        temperature: event.target.value,
                      }))
                    }
                  />
                </div>
                <div>
                  <p className={labelClass}>Reasoning effort</p>
                  <Select
                    value={newCardDraft.reasoningEffort}
                    onValueChange={(value) =>
                      setNewCardDraft((current) => ({
                        ...current,
                        reasoningEffort: value as "low" | "medium" | "high",
                      }))
                    }
                  >
                    <SelectTrigger className="mt-1 h-9 border-marketing-border bg-marketing-surface">
                      <SelectValue placeholder="Effort" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-end">
                  <label className="flex h-9 w-full items-center gap-2 rounded-lg border border-marketing-border bg-marketing-surface px-3 text-sm text-marketing-text-secondary">
                    <input
                      type="checkbox"
                      checked={newCardDraft.reasoningEnabled}
                      onChange={(event) =>
                        setNewCardDraft((current) => ({
                          ...current,
                          reasoningEnabled: event.target.checked,
                        }))
                      }
                      className="size-4 rounded border-marketing-border"
                    />
                    Enable reasoning
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-2 border-t border-marketing-border pt-3">
                <Dialog.Close asChild>
                  <Button
                    type="button"
                    variant="outline"
                    className="border-marketing-border"
                    disabled={isWorking}
                  >
                    Cancel
                  </Button>
                </Dialog.Close>
                <Button
                  type="submit"
                  disabled={isWorking}
                  className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
                >
                  <Plus className="size-4" aria-hidden="true" />
                  Create model card
                </Button>
              </div>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      <Dialog.Root
        open={Boolean(editingCard && editingDraft)}
        onOpenChange={(open) => {
          if (!open) {
            setEditingModelId(null);
          }
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-[140] bg-black/60 backdrop-blur-[1px]" />
          <Dialog.Content className="fixed top-1/2 left-1/2 z-[150] flex w-[min(94vw,36rem)] -translate-x-1/2 -translate-y-1/2 flex-col rounded-2xl border border-marketing-border bg-marketing-surface shadow-marketing-glow">
            <div className="flex items-start justify-between border-b border-marketing-border px-5 py-4">
              <div>
                <Dialog.Title className="text-lg font-semibold text-marketing-text-primary">
                  Edit Model Card
                </Dialog.Title>
                <Dialog.Description className="mt-1 text-sm text-marketing-text-secondary">
                  Update model settings and save changes.
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 rounded-md text-marketing-text-muted hover:bg-marketing-accent-medium hover:text-marketing-text-primary"
                >
                  <X className="size-4" aria-hidden="true" />
                </Button>
              </Dialog.Close>
            </div>

            {editingCard && editingDraft ? (
              <form
                className="space-y-4 px-5 py-4"
                onSubmit={(event) => {
                  event.preventDefault();
                  void (async () => {
                    const ok = await saveCard(editingCard.id);
                    if (ok) {
                      setEditingModelId(null);
                    }
                  })();
                }}
              >
                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <label className={labelClass} htmlFor="edit-display-name">
                      Display name
                    </label>
                    <input
                      id="edit-display-name"
                      className={`${fieldClass} mt-1`}
                      value={editingDraft.displayName}
                      onChange={(event) =>
                        updateDraft(
                          editingCard.id,
                          "displayName",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <label className={labelClass} htmlFor="edit-model-name">
                      Model name
                    </label>
                    <input
                      id="edit-model-name"
                      className={`${fieldClass} mt-1`}
                      value={editingDraft.modelName}
                      onChange={(event) =>
                        updateDraft(
                          editingCard.id,
                          "modelName",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <label className={labelClass} htmlFor="edit-base-url">
                      Base URL
                    </label>
                    <input
                      id="edit-base-url"
                      className={`${fieldClass} mt-1`}
                      value={editingDraft.baseUrl}
                      onChange={(event) =>
                        updateDraft(
                          editingCard.id,
                          "baseUrl",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <label className={labelClass} htmlFor="edit-temperature">
                      Temperature
                    </label>
                    <input
                      id="edit-temperature"
                      type="number"
                      min={0}
                      max={2}
                      step={0.1}
                      className={`${fieldClass} mt-1`}
                      value={editingDraft.temperature}
                      onChange={(event) =>
                        updateDraft(
                          editingCard.id,
                          "temperature",
                          event.target.value,
                        )
                      }
                    />
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div>
                    <p className={labelClass}>Reasoning effort</p>
                    <Select
                      value={editingDraft.reasoningEffort}
                      onValueChange={(value) =>
                        updateDraft(
                          editingCard.id,
                          "reasoningEffort",
                          value as "low" | "medium" | "high",
                        )
                      }
                    >
                      <SelectTrigger className="mt-1 h-9 border-marketing-border bg-marketing-surface">
                        <SelectValue placeholder="Effort" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="low">Low</SelectItem>
                        <SelectItem value="medium">Medium</SelectItem>
                        <SelectItem value="high">High</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-end">
                    <label className="flex h-9 w-full items-center gap-2 rounded-lg border border-marketing-border bg-marketing-surface px-3 text-sm text-marketing-text-secondary">
                      <input
                        type="checkbox"
                        checked={editingDraft.reasoningEnabled}
                        onChange={(event) =>
                          updateDraft(
                            editingCard.id,
                            "reasoningEnabled",
                            event.target.checked,
                          )
                        }
                        className="size-4 rounded border-marketing-border"
                      />
                      Enable reasoning
                    </label>
                  </div>
                </div>

                <div className="rounded-xl border border-marketing-border bg-marketing-accent-soft p-3">
                  <p className="text-xs text-marketing-text-secondary">
                    Current API key:{" "}
                    {editingCard.has_api_key
                      ? editingCard.api_key_preview || "[masked]"
                      : "Not configured"}
                  </p>
                  <input
                    type="password"
                    className={`${fieldClass} mt-2`}
                    value={editingDraft.replacementApiKey}
                    onChange={(event) =>
                      setReplacementApiKey(editingCard.id, event.target.value)
                    }
                    placeholder="Enter new API key or leave empty"
                  />
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      className="h-8 border-marketing-border px-2 text-xs"
                      onClick={() => markClearApiKey(editingCard.id)}
                    >
                      Clear on save
                    </Button>
                    {editingDraft.pendingClearKey ? (
                      <Button
                        type="button"
                        variant="outline"
                        className="h-8 border-marketing-border px-2 text-xs"
                        onClick={() => cancelClearApiKey(editingCard.id)}
                      >
                        Undo clear
                      </Button>
                    ) : null}
                  </div>
                </div>

                <div className="flex justify-end gap-2 border-t border-marketing-border pt-3">
                  <Dialog.Close asChild>
                    <Button
                      type="button"
                      variant="outline"
                      className="border-marketing-border"
                      disabled={isWorking}
                    >
                      Cancel
                    </Button>
                  </Dialog.Close>
                  <Button
                    type="submit"
                    disabled={isWorking}
                    className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
                  >
                    <Save className="size-4" aria-hidden="true" />
                    Save changes
                  </Button>
                </div>
              </form>
            ) : null}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
