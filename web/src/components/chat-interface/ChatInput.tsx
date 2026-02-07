import { Mic, Paperclip, SendHorizontal } from "lucide-react";
import type { ChangeEvent, KeyboardEvent, RefObject } from "react";
import { useRef } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const iconClass = "size-[18px]";
const gradientClass =
  "bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to";

export type PendingAttachment = {
  id: string;
  filename: string;
  sizeBytes: number;
  status: "uploading" | "ready" | "error";
  error?: string;
};

type ChatInputProps = {
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  value: string;
  onChange: (value: string) => void;
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  onSend: () => void;
  canSend: boolean;
  attachments: PendingAttachment[];
  onPickFiles: (files: FileList) => void;
  onRemoveAttachment: (attachmentId: string) => void;
  brandVoice: string;
  onToggleBrandVoice: () => void;
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
  canSend,
  attachments,
  onPickFiles,
  onRemoveAttachment,
  brandVoice,
  onToggleBrandVoice,
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
    <div className="border-t border-marketing-border bg-marketing-surface-translucent p-4 backdrop-blur-[12px] md:px-8 md:py-6">
      <div className="mx-auto max-w-[900px]">
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
            "flex items-end gap-3 rounded-2xl border-2 border-marketing-border bg-marketing-surface py-2 pr-2 pl-5 transition-all duration-300",
            "shadow-marketing-soft",
            "focus-within:border-marketing-secondary focus-within:ring-4 focus-within:ring-marketing-accent-glow",
          )}
        >
          <div className="flex-1">
            {attachments.length > 0 ? (
              <div className="mb-2 flex flex-wrap gap-2">
                {attachments.map((attachment) => (
                  <div
                    key={attachment.id}
                    className={cn(
                      "flex items-center gap-2 rounded-lg border px-2 py-1 text-xs",
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
              className="min-h-0 max-h-[150px] flex-1 resize-none border-0 bg-transparent px-0 py-3 text-base text-marketing-text-primary placeholder:text-marketing-text-muted shadow-none focus-visible:ring-0"
              placeholder="Ask me to write ad copy, optimize SEO, or plan a campaign..."
              rows={1}
              value={value}
              onChange={(event) => onChange(event.target.value)}
              onKeyDown={onKeyDown}
            />
          </div>
          <div className="flex gap-2 pb-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 rounded-lg text-marketing-text-muted hover:bg-marketing-accent-medium hover:text-marketing-primary"
              type="button"
              title="Attach"
              onClick={() => fileInputRef.current?.click()}
            >
              <Paperclip className={iconClass} aria-hidden="true" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 rounded-lg text-marketing-text-muted hover:bg-marketing-accent-medium hover:text-marketing-primary"
              type="button"
              title="Voice"
            >
              <Mic className={iconClass} aria-hidden="true" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className={cn(
                "h-10 w-10 rounded-xl text-marketing-on-primary transition-all duration-200 hover:text-marketing-on-primary",
                gradientClass,
                "shadow-marketing-soft",
                "hover:scale-105 hover:-rotate-6 hover:shadow-marketing-hover",
              )}
              type="button"
              onClick={onSend}
              disabled={!canSend}
            >
              <SendHorizontal className={iconClass} aria-hidden="true" />
            </Button>
          </div>
        </div>
        <div className="mt-3 flex flex-col items-start gap-3 px-2 text-xs text-marketing-text-muted md:flex-row md:items-center md:justify-between">
          <span>AI can make mistakes. Verify important data.</span>
          <Button
            type="button"
            variant="ghost"
            className="h-auto rounded-full border-0 bg-marketing-accent-medium px-2.5 py-1 text-xs font-semibold text-marketing-primary hover:bg-marketing-accent-strong hover:text-marketing-primary"
            onClick={onToggleBrandVoice}
          >
            <span
              className="h-2 w-2 rounded-full bg-marketing-primary"
              aria-hidden="true"
            />
            <span>{brandVoice}</span>
            <span className="text-xs leading-none" aria-hidden="true">
              v
            </span>
          </Button>
        </div>
      </div>
    </div>
  );
}
