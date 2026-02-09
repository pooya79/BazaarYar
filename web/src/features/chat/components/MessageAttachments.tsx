import { FileSpreadsheet, FileText, Image as ImageIcon } from "lucide-react";
import type { MessageAttachment } from "@/features/chat/model/types";
import { cn } from "@/shared/lib/utils";

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

type MessageAttachmentsProps = {
  attachments: MessageAttachment[];
  className?: string;
};

export function MessageAttachments({
  attachments,
  className,
}: MessageAttachmentsProps) {
  if (attachments.length === 0) {
    return null;
  }

  return (
    <div className={cn("space-y-2", className)}>
      {attachments.map((attachment) => (
        <div
          key={attachment.id}
          className="rounded-lg border border-marketing-border bg-marketing-surface-translucent p-3"
        >
          <div className="flex items-center gap-2 text-sm">
            <AttachmentIcon mediaType={attachment.mediaType} />
            <span className="truncate font-medium">{attachment.filename}</span>
            <span className="ml-auto text-xs text-marketing-text-muted">
              {formatBytes(attachment.sizeBytes)}
            </span>
          </div>
          {attachment.mediaType === "image" && attachment.localPreviewUrl ? (
            /* biome-ignore lint/performance/noImgElement: Blob previews and direct download URLs require raw img src. */
            <img
              src={attachment.localPreviewUrl}
              alt={attachment.filename}
              className="mt-2 max-h-52 w-full rounded-lg border border-marketing-border object-contain bg-marketing-bg"
            />
          ) : null}
        </div>
      ))}
    </div>
  );
}
