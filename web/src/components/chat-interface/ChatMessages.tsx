import {
  Bot,
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
  User,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { Message } from "./types";

const iconClass = "size-[18px]";

const bubbleBaseClass =
  "rounded-xl border border-marketing-border bg-marketing-surface text-marketing-text-primary shadow-marketing-subtle";

const bubbleContentClass =
  "px-4 py-3.5 leading-relaxed whitespace-pre-line text-[0.9375rem]";

type ChatMessagesProps = {
  messages: Message[];
  isTyping: boolean;
};

function formatBytes(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function AttachmentIcon({
  mediaType,
}: {
  mediaType: "image" | "pdf" | "text" | "spreadsheet" | "binary";
}) {
  if (mediaType === "image") {
    return <ImageIcon className="size-4" aria-hidden="true" />;
  }
  if (mediaType === "spreadsheet") {
    return <FileSpreadsheet className="size-4" aria-hidden="true" />;
  }
  return <FileText className="size-4" aria-hidden="true" />;
}

export function ChatMessages({ messages, isTyping }: ChatMessagesProps) {
  return (
    <div className="mx-auto flex w-full max-w-[800px] flex-col gap-8">
      {messages.map((message) => (
        <div
          key={message.id}
          className={cn(
            "flex gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300",
            message.sender === "user" && "flex-row-reverse",
          )}
        >
          <div
            className={cn(
              "flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border text-[0.75rem] font-semibold shadow-none",
              message.sender === "bot"
                ? "border-transparent bg-marketing-primary text-marketing-on-primary"
                : "border-marketing-border bg-secondary text-marketing-text-secondary",
            )}
          >
            {message.sender === "bot" ? (
              <Bot className={iconClass} aria-hidden="true" />
            ) : (
              <User className={iconClass} aria-hidden="true" />
            )}
          </div>
          <div className="flex max-w-[70%] flex-col gap-1">
            {message.sender === "bot" && message.kind && (
              <div className="px-1 text-[0.65rem] uppercase tracking-[0.08em] text-marketing-text-muted">
                {message.kind.replace("_", " ")}
              </div>
            )}
            <Card
              className={cn(
                "gap-0 py-0",
                bubbleBaseClass,
                message.sender === "user"
                  ? "rounded-bl-xl rounded-br-[4px] border-0 bg-marketing-text-primary text-marketing-on-primary"
                  : "rounded-bl-[4px]",
                message.kind === "reasoning" &&
                  "border-dashed text-marketing-text-muted",
                message.kind === "meta" &&
                  "border-dashed text-marketing-text-muted",
                (message.kind === "tool_call" ||
                  message.kind === "tool_result") &&
                  "border-marketing-border/80",
              )}
            >
              <CardContent
                className={cn(
                  bubbleContentClass,
                  (message.kind === "tool_call" ||
                    message.kind === "tool_result") &&
                    "font-mono text-[0.95rem]",
                )}
              >
                <div className="flex flex-col gap-3">
                  {message.text ? <div>{message.text}</div> : null}
                  {message.attachments && message.attachments.length > 0 ? (
                    <div className="space-y-2">
                      {message.attachments.map((attachment) => (
                        <div
                          key={attachment.id}
                          className="rounded-lg border border-marketing-border bg-marketing-surface-translucent p-3"
                        >
                          <div className="flex items-center gap-2 text-sm">
                            <AttachmentIcon mediaType={attachment.mediaType} />
                            <span className="truncate font-medium">
                              {attachment.filename}
                            </span>
                            <span className="ml-auto text-xs text-marketing-text-muted">
                              {formatBytes(attachment.sizeBytes)}
                            </span>
                          </div>
                          {attachment.mediaType === "image" &&
                          attachment.localPreviewUrl ? (
                            /* biome-ignore lint/performance/noImgElement: Blob previews must use a direct object URL source. */
                            <img
                              src={attachment.localPreviewUrl}
                              alt={attachment.filename}
                              className="mt-2 max-h-52 w-full rounded-lg border border-marketing-border object-contain bg-marketing-bg"
                            />
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              </CardContent>
            </Card>
            <div className="px-1 text-[0.7rem] text-marketing-text-muted">
              {message.time}
            </div>
          </div>
        </div>
      ))}

      {isTyping && (
        <div className="flex gap-4">
          <div
            className={cn(
              "flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-marketing-primary text-marketing-on-primary",
            )}
          >
            <Bot className={iconClass} aria-hidden="true" />
          </div>
          <div className="flex max-w-[70%] flex-col gap-1">
            <Card
              className={cn(
                "gap-0 py-0 rounded-xl rounded-bl-[4px]",
                bubbleBaseClass,
              )}
            >
              <CardContent className={bubbleContentClass}>
                <div className="flex gap-1 px-2 py-1">
                  <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-marketing-primary" />
                  <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-marketing-primary [animation-delay:0.2s]" />
                  <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-marketing-primary [animation-delay:0.4s]" />
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
