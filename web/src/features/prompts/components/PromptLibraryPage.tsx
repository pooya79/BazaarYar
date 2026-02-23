"use client";

import { ChevronDown, Edit3, FileCode2, Plus, Trash2 } from "lucide-react";
import { PromptEditorModal } from "@/features/prompts/components/PromptEditorModal";
import { usePromptLibrary } from "@/features/prompts/hooks/usePromptLibrary";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeStyle: "short",
});

const formatDate = (value: string) => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return dateFormatter.format(parsed);
};

export function PromptLibraryPage() {
  const {
    prompts,
    isLoading,
    error,
    isEditorOpen,
    editorMode,
    expandedPromptId,
    commandName,
    description,
    promptBody,
    formError,
    isSubmitting,
    setCommandName,
    setDescription,
    setPromptBody,
    setExpandedPromptId,
    openCreateEditor,
    openEditEditor,
    closeEditor,
    submitEditor,
    deletePrompt,
    deletingPromptId,
  } = usePromptLibrary();

  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-6 py-6 md:px-10 md:py-8">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-4">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-marketing-text-primary">
              Prompt Library
            </h1>
            <p className="mt-1 text-sm text-marketing-text-secondary">
              Create reusable prompt commands and trigger them in chat with
              <span className="font-mono"> \name</span>.
            </p>
          </div>
          <Button
            type="button"
            size="icon"
            className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
            onClick={openCreateEditor}
            aria-label="Create prompt"
          >
            <Plus className="size-4" aria-hidden="true" />
          </Button>
        </header>

        <section className="rounded-2xl border border-marketing-border bg-marketing-surface p-4 shadow-marketing-subtle">
          {isLoading ? (
            <div className="rounded-lg border border-marketing-border bg-marketing-bg px-3 py-4 text-sm text-marketing-text-muted">
              Loading prompts...
            </div>
          ) : null}

          {error ? (
            <div className="mb-3 rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
              {error}
            </div>
          ) : null}

          {!isLoading && prompts.length === 0 ? (
            <div className="rounded-lg border border-dashed border-marketing-border bg-marketing-bg px-3 py-6 text-center text-sm text-marketing-text-muted">
              No prompts yet. Click the plus button to create one.
            </div>
          ) : null}

          <div className="grid gap-3 md:grid-cols-2">
            {prompts.map((prompt) => {
              const isExpanded = expandedPromptId === prompt.id;
              return (
                <article
                  key={prompt.id}
                  className="rounded-xl border border-marketing-border bg-marketing-bg p-3"
                >
                  <div className="mb-2 flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <FileCode2
                          className="size-4 shrink-0 text-marketing-primary"
                          aria-hidden="true"
                        />
                        <h2 className="truncate text-sm font-semibold text-marketing-text-primary">
                          <span className="font-mono">\{prompt.name}</span>
                        </h2>
                      </div>
                      <p className="mt-1 line-clamp-2 text-sm text-marketing-text-secondary">
                        {prompt.description || "No description"}
                      </p>
                    </div>
                  </div>

                  <div className="mb-3 flex flex-wrap gap-3 text-xs text-marketing-text-muted">
                    <span>Updated: {formatDate(prompt.updated_at)}</span>
                    <span>Created: {formatDate(prompt.created_at)}</span>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="border-marketing-border"
                      onClick={() =>
                        setExpandedPromptId(isExpanded ? null : prompt.id)
                      }
                    >
                      <ChevronDown
                        className={cn(
                          "size-4 transition-transform",
                          isExpanded && "rotate-180",
                        )}
                        aria-hidden="true"
                      />
                      {isExpanded ? "Hide prompt" : "Show prompt"}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="border-marketing-border"
                      onClick={() => openEditEditor(prompt.id)}
                    >
                      <Edit3 className="size-4" aria-hidden="true" />
                      Edit
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="border-marketing-danger text-marketing-danger hover:bg-marketing-danger-soft"
                      onClick={() => deletePrompt(prompt.id)}
                      disabled={deletingPromptId === prompt.id}
                    >
                      <Trash2 className="size-4" aria-hidden="true" />
                      {deletingPromptId === prompt.id
                        ? "Deleting..."
                        : "Delete"}
                    </Button>
                  </div>

                  {isExpanded ? (
                    <div className="mt-3 rounded-lg border border-marketing-border bg-marketing-surface p-3 text-sm text-marketing-text-primary">
                      <pre className="whitespace-pre-wrap font-sans">
                        {prompt.prompt}
                      </pre>
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>
        </section>
      </div>

      <PromptEditorModal
        open={isEditorOpen}
        mode={editorMode}
        commandName={commandName}
        description={description}
        promptBody={promptBody}
        isSubmitting={isSubmitting}
        formError={formError}
        onCommandNameChange={setCommandName}
        onDescriptionChange={setDescription}
        onPromptBodyChange={setPromptBody}
        onOpenChange={(open) => {
          if (!open) {
            closeEditor();
          }
        }}
        onCancel={closeEditor}
        onSubmit={submitEditor}
      />
    </div>
  );
}
