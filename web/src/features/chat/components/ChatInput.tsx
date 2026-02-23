import {
  Paperclip,
  SendHorizontal,
  SlidersHorizontal,
  Square,
} from "lucide-react";
import type { ChangeEvent, KeyboardEvent, RefObject } from "react";
import { useRef } from "react";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { Textarea } from "@/shared/ui/textarea";

const iconClass = "size-[18px]";

export type PendingAttachment = {
  id: string;
  filename: string;
  sizeBytes: number;
  status: "uploading" | "ready" | "error";
  error?: string;
};

export type PromptSuggestion = {
  id: string;
  name: string;
  description: string;
  prompt: string;
};

type ChatInputProps = {
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  value: string;
  onChange: (value: string) => void;
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  onSend: () => void;
  isStreaming: boolean;
  onStop: () => void;
  canSend: boolean;
  attachments: PendingAttachment[];
  onPickFiles: (files: FileList) => void;
  onRemoveAttachment: (attachmentId: string) => void;
  onOpenToolSettings: () => void;
  toolSettingsBusy: boolean;
  promptSuggestions: PromptSuggestion[];
  activePromptSuggestionIndex: number;
  onPromptSuggestionHover: (index: number) => void;
  onPromptSuggestionSelect: (index: number) => void;
};

function formatBytes(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function ChatInput({
  textareaRef,
  value,
  onChange,
  onKeyDown,
  onSend,
  isStreaming,
  onStop,
  canSend,
  attachments,
  onPickFiles,
  onRemoveAttachment,
  onOpenToolSettings,
  toolSettingsBusy,
  promptSuggestions,
  activePromptSuggestionIndex,
  onPromptSuggestionHover,
  onPromptSuggestionSelect,
}: ChatInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (!event.target.files || event.target.files.length === 0) {
      return;
    }
    onPickFiles(event.target.files);
    event.target.value = "";
  };

  return (
    <div className="border-t border-marketing-border bg-marketing-surface-translucent px-6 py-4 backdrop-blur-[12px] md:px-10 md:py-6">
      <div className="mx-auto max-w-[800px]">
        {promptSuggestions.length > 0 ? (
          <div className="mb-3 overflow-hidden rounded-lg border border-marketing-border bg-marketing-surface shadow-marketing-soft">
            <div className="border-b border-marketing-border px-3 py-2 text-[0.68rem] font-semibold uppercase tracking-[0.08em] text-marketing-text-muted">
              Prompt Library Matches
            </div>
            <ul className="divide-y divide-marketing-border">
              {promptSuggestions.map((suggestion, index) => (
                <li
                  key={suggestion.id}
                  className={cn(
                    "[animation:promptSuggestionBounce_280ms_cubic-bezier(0.34,1.56,0.64,1)_both]",
                  )}
                  style={{ animationDelay: `${index * 55}ms` }}
                >
                  <button
                    type="button"
                    className={cn(
                      "flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left transition-colors",
                      activePromptSuggestionIndex === index
                        ? "bg-marketing-accent-soft"
                        : "hover:bg-marketing-accent-medium",
                    )}
                    onMouseEnter={() => onPromptSuggestionHover(index)}
                    onMouseDown={(event) => {
                      event.preventDefault();
                      onPromptSuggestionSelect(index);
                    }}
                  >
                    <span className="font-mono text-sm font-semibold text-marketing-primary">
                      \{suggestion.name}
                    </span>
                    <span className="line-clamp-1 text-xs text-marketing-text-secondary">
                      {suggestion.description || "No description"}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <input
          ref={fileInputRef}
          className="hidden"
          type="file"
          multiple
          accept=".png,.jpg,.jpeg,.webp,.gif,.pdf,.txt,.csv,.tsv,.xlsx,.xls,image/*,application/pdf,text/plain,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          onChange={handleFileChange}
        />
        <div
          className={cn(
            "flex items-end gap-3 rounded-lg border border-input bg-marketing-surface py-2 pr-2 pl-4 transition-all duration-200",
            "shadow-marketing-soft",
            "focus-within:border-marketing-primary focus-within:ring-4 focus-within:ring-marketing-accent-glow",
          )}
        >
          <div className="flex-1">
            {attachments.length > 0 ? (
              <div className="mb-2 flex flex-wrap gap-2">
                {attachments.map((attachment) => (
                  <div
                    key={attachment.id}
                    className={cn(
                      "flex items-center gap-2 rounded-md border px-2 py-1 text-xs",
                      attachment.status === "error"
                        ? "border-marketing-border border-dashed bg-marketing-surface-translucent text-marketing-text-muted"
                        : "border-marketing-border bg-marketing-surface-translucent text-marketing-text-primary",
                    )}
                  >
                    <span className="max-w-52 truncate">
                      {attachment.filename}
                    </span>
                    <span className="text-marketing-text-muted">
                      {formatBytes(attachment.sizeBytes)}
                    </span>
                    <span className="text-marketing-text-muted">
                      {attachment.status === "uploading" ? "Uploading..." : ""}
                      {attachment.status === "error"
                        ? attachment.error || "Upload failed"
                        : ""}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-5 w-5 rounded-full text-marketing-text-muted hover:bg-marketing-accent-medium hover:text-marketing-primary"
                      onClick={() => onRemoveAttachment(attachment.id)}
                    >
                      x
                    </Button>
                  </div>
                ))}
              </div>
            ) : null}
            <Textarea
              ref={textareaRef}
              className="min-h-0 max-h-[120px] flex-1 resize-none border-0 bg-transparent px-0 py-2 text-[0.9375rem] text-marketing-text-primary placeholder:text-marketing-text-muted shadow-none focus-visible:ring-0"
              placeholder="Ask me to write ad copy, optimize SEO, or plan a campaign..."
              rows={1}
              value={value}
              onChange={(event) => onChange(event.target.value)}
              onKeyDown={onKeyDown}
            />
          </div>
          <div className="flex gap-1 pb-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 rounded-md text-marketing-text-muted hover:bg-marketing-accent-medium hover:text-marketing-text-primary"
              type="button"
              title="Attach"
              onClick={() => fileInputRef.current?.click()}
            >
              <Paperclip className={iconClass} aria-hidden="true" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 rounded-md text-marketing-text-muted hover:bg-marketing-accent-medium hover:text-marketing-text-primary"
              type="button"
              title="Tools"
              onClick={onOpenToolSettings}
              disabled={toolSettingsBusy}
            >
              <SlidersHorizontal className={iconClass} aria-hidden="true" />
            </Button>
            {isStreaming ? (
              <Button
                variant="ghost"
                size="icon"
                className="ml-1 h-8 w-8 rounded-md bg-marketing-secondary text-marketing-on-primary shadow-marketing-soft transition-colors duration-150 hover:bg-marketing-primary hover:text-marketing-on-primary"
                type="button"
                onClick={onStop}
                title="Stop generating"
              >
                <Square className={iconClass} aria-hidden="true" />
              </Button>
            ) : (
              <Button
                variant="ghost"
                size="icon"
                className={cn(
                  "ml-1 h-8 w-8 rounded-md bg-marketing-primary text-marketing-on-primary shadow-marketing-soft transition-colors duration-150 hover:bg-marketing-secondary hover:text-marketing-on-primary",
                  "disabled:pointer-events-none disabled:bg-marketing-border disabled:text-marketing-text-muted",
                )}
                type="button"
                onClick={onSend}
                disabled={!canSend}
              >
                <SendHorizontal className={iconClass} aria-hidden="true" />
              </Button>
            )}
          </div>
        </div>
        <div className="mt-3 px-1 text-[0.7rem] text-marketing-text-muted">
          <span>AI can make mistakes. Verify important data.</span>
        </div>
      </div>
    </div>
  );
}
