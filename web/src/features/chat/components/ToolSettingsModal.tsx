"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Loader2, Wrench, X } from "lucide-react";
import type { ToolCatalogGroup } from "@/shared/api/schemas/settings";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/shared/ui/accordion";
import { Button } from "@/shared/ui/button";

type ToolSettingsModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  groups: ToolCatalogGroup[];
  isLoading: boolean;
  isSaving: boolean;
  hasUnsavedChanges: boolean;
  loadError: string | null;
  saveError: string | null;
  onToggleGroup: (groupKey: string, enabled: boolean) => void;
  onToggleTool: (toolKey: string, enabled: boolean) => void;
  onReload: () => void;
  onSave: () => Promise<boolean>;
  onDiscard: () => void;
};

const panelClass =
  "rounded-xl border border-marketing-border bg-marketing-accent-soft p-1";

export function ToolSettingsModal({
  open,
  onOpenChange,
  groups,
  isLoading,
  isSaving,
  hasUnsavedChanges,
  loadError,
  saveError,
  onToggleGroup,
  onToggleTool,
  onReload,
  onSave,
  onDiscard,
}: ToolSettingsModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[140] bg-black/60 backdrop-blur-[1px]" />
        <Dialog.Content className="fixed top-1/2 left-1/2 z-[150] flex h-[min(88vh,40rem)] w-[min(94vw,34rem)] -translate-x-1/2 -translate-y-1/2 flex-col rounded-2xl border border-marketing-border bg-marketing-surface shadow-marketing-glow">
          <div className="flex items-start justify-between border-b border-marketing-border p-5">
            <div>
              <Dialog.Title className="text-lg font-semibold text-marketing-text-primary">
                Tool settings
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-marketing-text-secondary">
                Choose groups and tools, then save your changes.
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="inline-flex size-9 items-center justify-center rounded-lg border border-marketing-border bg-marketing-surface text-marketing-text-secondary transition-colors hover:text-marketing-text-primary"
                aria-label="Close"
              >
                <X className="size-4" aria-hidden="true" />
              </button>
            </Dialog.Close>
          </div>

          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-5">
            {isLoading ? (
              <div className="flex items-center gap-2 rounded-lg border border-marketing-border bg-marketing-bg px-3 py-3 text-sm text-marketing-text-secondary">
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                Loading tools...
              </div>
            ) : null}

            {!isLoading && loadError ? (
              <div className="space-y-2 rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-3 text-sm text-marketing-danger">
                <div>{loadError}</div>
                <Button
                  type="button"
                  variant="outline"
                  className="border-marketing-danger text-marketing-danger hover:bg-marketing-danger-soft"
                  onClick={onReload}
                >
                  Retry
                </Button>
              </div>
            ) : null}

            {!isLoading && !loadError && groups.length > 0 ? (
              <Accordion type="multiple" className={panelClass}>
                {groups.map((group) => {
                  return (
                    <AccordionItem
                      key={group.key}
                      value={group.key}
                      className="mx-2 border-marketing-border"
                    >
                      <AccordionTrigger className="px-2 py-3 hover:no-underline">
                        <div className="flex w-full items-center justify-between gap-3 pr-2">
                          <div>
                            <div className="text-sm font-semibold text-marketing-text-primary">
                              {group.label}
                            </div>
                            <div className="text-xs text-marketing-text-muted">
                              {group.enabled
                                ? "At least one tool is enabled"
                                : "All tools in this group are disabled"}
                            </div>
                          </div>

                          <label className="inline-flex items-center gap-2 text-xs text-marketing-text-secondary">
                            <input
                              type="checkbox"
                              className="size-4 rounded border-marketing-border"
                              checked={group.enabled}
                              disabled={isSaving}
                              onClick={(event) => event.stopPropagation()}
                              onChange={(event) => {
                                onToggleGroup(group.key, event.target.checked);
                              }}
                            />
                            Enabled
                          </label>
                        </div>
                      </AccordionTrigger>

                      <AccordionContent className="space-y-2 px-2 pb-3">
                        {group.tools.map((tool) => {
                          const unavailable = !tool.available;

                          return (
                            <div
                              key={tool.key}
                              className="rounded-lg border border-marketing-border bg-marketing-surface px-3 py-2"
                            >
                              <div className="flex items-center justify-between gap-3">
                                <div className="min-w-0">
                                  <div className="truncate text-sm text-marketing-text-primary">
                                    {tool.label}
                                  </div>
                                  <div className="line-clamp-2 text-xs text-marketing-text-muted">
                                    {tool.description}
                                  </div>
                                </div>

                                <label className="inline-flex shrink-0 items-center gap-2 text-xs text-marketing-text-secondary">
                                  <input
                                    type="checkbox"
                                    className="size-4 rounded border-marketing-border"
                                    checked={tool.enabled}
                                    disabled={isSaving || unavailable}
                                    onChange={(event) => {
                                      onToggleTool(
                                        tool.key,
                                        event.target.checked,
                                      );
                                    }}
                                  />
                                </label>
                              </div>

                              {unavailable && tool.unavailable_reason ? (
                                <div className="mt-1 text-xs text-marketing-text-muted">
                                  {tool.unavailable_reason}
                                </div>
                              ) : null}
                            </div>
                          );
                        })}
                      </AccordionContent>
                    </AccordionItem>
                  );
                })}
              </Accordion>
            ) : null}

            {!isLoading && !loadError && groups.length === 0 ? (
              <div className="rounded-lg border border-marketing-border bg-marketing-bg px-3 py-4 text-sm text-marketing-text-muted">
                No tools available.
              </div>
            ) : null}

            {saveError ? (
              <div className="rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
                {saveError}
              </div>
            ) : null}
          </div>

          <div className="flex items-center justify-between border-t border-marketing-border px-5 py-3 text-xs text-marketing-text-muted">
            <div className="inline-flex items-center gap-2">
              <Wrench className="size-3.5" aria-hidden="true" />
              {hasUnsavedChanges ? "Unsaved changes" : "Saved globally"}
            </div>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                className="border-marketing-border"
                onClick={onDiscard}
                disabled={isSaving || !hasUnsavedChanges}
              >
                Discard
              </Button>
              <Button
                type="button"
                className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
                onClick={() => {
                  void onSave();
                }}
                disabled={
                  isSaving || !hasUnsavedChanges || isLoading || !!loadError
                }
              >
                {isSaving ? (
                  <>
                    <Loader2
                      className="size-4 animate-spin"
                      aria-hidden="true"
                    />
                    Saving...
                  </>
                ) : (
                  "Save"
                )}
              </Button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
