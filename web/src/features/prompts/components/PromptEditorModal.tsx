"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { FormEvent } from "react";
import type { PromptEditorMode } from "@/features/prompts/hooks/usePromptLibrary";
import { normalizePromptCommandName } from "@/features/prompts/model/promptStore";
import { Button } from "@/shared/ui/button";
import { Textarea } from "@/shared/ui/textarea";

const fieldClass =
  "h-10 w-full rounded-lg border border-marketing-border bg-marketing-surface px-3 text-sm text-marketing-text-primary outline-none transition-colors focus:border-marketing-primary";

const labelClass =
  "text-[0.68rem] font-semibold uppercase tracking-[0.08em] text-marketing-text-muted";

type PromptEditorModalProps = {
  open: boolean;
  mode: PromptEditorMode;
  commandName: string;
  description: string;
  promptBody: string;
  isSubmitting: boolean;
  formError: string | null;
  onCommandNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onPromptBodyChange: (value: string) => void;
  onOpenChange: (open: boolean) => void;
  onCancel: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

export function PromptEditorModal({
  open,
  mode,
  commandName,
  description,
  promptBody,
  isSubmitting,
  formError,
  onCommandNameChange,
  onDescriptionChange,
  onPromptBodyChange,
  onOpenChange,
  onCancel,
  onSubmit,
}: PromptEditorModalProps) {
  const isCreateMode = mode === "create";
  const previewCommandName = normalizePromptCommandName(commandName) || "name";

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-[140] bg-black/60 backdrop-blur-[1px]" />
        <Dialog.Content className="fixed top-1/2 left-1/2 z-[150] flex h-[min(90vh,42rem)] w-[min(94vw,44rem)] -translate-x-1/2 -translate-y-1/2 flex-col rounded-2xl border border-marketing-border bg-marketing-surface shadow-marketing-glow">
          <div className="flex items-start justify-between border-b border-marketing-border p-5">
            <div>
              <Dialog.Title className="text-lg font-semibold text-marketing-text-primary">
                {isCreateMode ? "Create prompt" : "Edit prompt"}
              </Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-marketing-text-secondary">
                {isCreateMode
                  ? "Add a reusable prompt command for chat."
                  : "Update this reusable prompt command."}
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

          <form onSubmit={onSubmit} className="flex min-h-0 flex-1 flex-col">
            <div className="flex-1 space-y-4 overflow-y-auto p-5">
              <div className="space-y-1">
                <label className={labelClass} htmlFor="prompt-modal-name">
                  Command name
                </label>
                <input
                  id="prompt-modal-name"
                  className={fieldClass}
                  value={commandName}
                  onChange={(event) => onCommandNameChange(event.target.value)}
                  placeholder="campaign-launch-plan"
                />
                <p className="text-xs text-marketing-text-muted">
                  Trigger with{" "}
                  <span className="font-mono">\{previewCommandName}</span>
                </p>
              </div>

              <div className="space-y-1">
                <label
                  className={labelClass}
                  htmlFor="prompt-modal-description"
                >
                  Description
                </label>
                <input
                  id="prompt-modal-description"
                  className={fieldClass}
                  value={description}
                  onChange={(event) => onDescriptionChange(event.target.value)}
                  maxLength={180}
                  placeholder="What this prompt should generate..."
                />
              </div>

              <div className="space-y-1">
                <label className={labelClass} htmlFor="prompt-modal-body">
                  Prompt
                </label>
                <Textarea
                  id="prompt-modal-body"
                  className="min-h-48 border-marketing-border text-marketing-text-primary"
                  value={promptBody}
                  onChange={(event) => onPromptBodyChange(event.target.value)}
                  placeholder="Write the reusable prompt text..."
                />
              </div>

              {formError ? (
                <div className="rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
                  {formError}
                </div>
              ) : null}
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-marketing-border p-5">
              <Button
                type="button"
                variant="outline"
                className="border-marketing-border"
                onClick={onCancel}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting}
                className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
              >
                {isSubmitting
                  ? isCreateMode
                    ? "Creating..."
                    : "Saving..."
                  : isCreateMode
                    ? "Create prompt"
                    : "Save changes"}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
