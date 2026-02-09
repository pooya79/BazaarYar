import { useCallback, useState } from "react";
import type { PendingAttachment } from "@/features/chat/components/ChatInput";
import type { MessageAttachment } from "@/features/chat/model/types";
import { uploadAgentAttachments } from "@/shared/api/clients/agent.client";

export type ComposerAttachment = PendingAttachment & {
  fileId?: string;
  contentType?: string;
  mediaType?: "image" | "pdf" | "text" | "spreadsheet" | "binary";
  previewText?: string | null;
  extractionNote?: string | null;
  localPreviewUrl?: string;
};

export type ReadyComposerAttachment = ComposerAttachment & {
  fileId: string;
  mediaType: NonNullable<ComposerAttachment["mediaType"]>;
};

function getErrorMessage(error: unknown) {
  if (error && typeof error === "object" && "message" in error) {
    return String((error as { message: unknown }).message);
  }
  return "Upload failed.";
}

export function isReadyComposerAttachment(
  item: ComposerAttachment,
): item is ReadyComposerAttachment {
  return (
    item.status === "ready" && Boolean(item.fileId) && Boolean(item.mediaType)
  );
}

export function toMessageAttachment(
  item: ReadyComposerAttachment,
): MessageAttachment {
  return {
    id: item.fileId,
    filename: item.filename,
    contentType: item.contentType || "application/octet-stream",
    mediaType: item.mediaType,
    sizeBytes: item.sizeBytes,
    previewText: item.previewText,
    extractionNote: item.extractionNote,
    localPreviewUrl: item.localPreviewUrl,
  };
}

export function useComposerAttachments() {
  const [pendingAttachments, setPendingAttachments] = useState<
    ComposerAttachment[]
  >([]);

  const handlePickFiles = useCallback(async (files: FileList) => {
    const fileList = Array.from(files);
    for (const file of fileList) {
      const tempId = `local-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const localPreviewUrl = file.type.startsWith("image/")
        ? URL.createObjectURL(file)
        : undefined;

      setPendingAttachments((prev) => [
        ...prev,
        {
          id: tempId,
          filename: file.name,
          sizeBytes: file.size,
          status: "uploading",
          localPreviewUrl,
        },
      ]);

      try {
        const [uploaded] = await uploadAgentAttachments([file]);
        if (!uploaded) {
          throw new Error("Upload returned no file metadata.");
        }
        setPendingAttachments((prev) =>
          prev.map((item) =>
            item.id === tempId
              ? {
                  ...item,
                  status: "ready",
                  fileId: uploaded.id,
                  contentType: uploaded.contentType,
                  mediaType: uploaded.mediaType,
                  previewText: uploaded.previewText,
                  extractionNote: uploaded.extractionNote,
                }
              : item,
          ),
        );
      } catch (error) {
        setPendingAttachments((prev) =>
          prev.map((item) =>
            item.id === tempId
              ? {
                  ...item,
                  status: "error",
                  error: getErrorMessage(error),
                }
              : item,
          ),
        );
      }
    }
  }, []);

  const handleRemoveAttachment = useCallback((attachmentId: string) => {
    setPendingAttachments((prev) => {
      const current = prev.find((item) => item.id === attachmentId);
      if (current?.localPreviewUrl) {
        URL.revokeObjectURL(current.localPreviewUrl);
      }
      return prev.filter((item) => item.id !== attachmentId);
    });
  }, []);

  const clearPendingAttachments = useCallback(() => {
    setPendingAttachments((prev) => {
      for (const attachment of prev) {
        if (attachment.localPreviewUrl) {
          URL.revokeObjectURL(attachment.localPreviewUrl);
        }
      }
      return [];
    });
  }, []);

  return {
    pendingAttachments,
    setPendingAttachments,
    handlePickFiles,
    handleRemoveAttachment,
    clearPendingAttachments,
  };
}
