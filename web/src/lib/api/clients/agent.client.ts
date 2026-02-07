import { buildUrl, normalizeError } from "../http";
import {
  streamEventSchema,
  uploadAttachmentsResponseSchema,
} from "../schemas/agent";
import type { StreamEvent } from "../types";

export type AgentChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type UploadedAttachment = {
  id: string;
  filename: string;
  contentType: string;
  mediaType: "image" | "pdf" | "text" | "spreadsheet" | "binary";
  sizeBytes: number;
  previewText?: string | null;
  extractionNote?: string | null;
};

export type StreamAgentOptions = {
  message: string;
  history?: AgentChatMessage[];
  attachmentIds?: string[];
  signal?: AbortSignal;
  onEvent: (event: StreamEvent) => void;
};

const parseSseBlock = (block: string) => {
  let eventName: string | undefined;
  const dataLines: string[] = [];

  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  return {
    event: eventName,
    data: dataLines.join("\n"),
  };
};

export async function uploadAgentAttachments(
  files: File[],
  signal?: AbortSignal,
): Promise<UploadedAttachment[]> {
  if (files.length === 0) {
    return [];
  }

  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  const response = await fetch(buildUrl("/api/agent/attachments"), {
    method: "POST",
    body: formData,
    signal,
  });

  if (!response.ok) {
    const text = await response.text();
    let payload: unknown = null;
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        payload = text;
      }
    }
    throw normalizeError(response, payload);
  }

  const payload = await response.json();
  const parsed = uploadAttachmentsResponseSchema.parse(payload);
  return parsed.files.map((item) => ({
    id: item.id,
    filename: item.filename,
    contentType: item.content_type,
    mediaType: item.media_type,
    sizeBytes: item.size_bytes,
    previewText: item.preview_text,
    extractionNote: item.extraction_note,
  }));
}

export async function streamAgent({
  message,
  history,
  attachmentIds,
  signal,
  onEvent,
}: StreamAgentOptions) {
  const response = await fetch(buildUrl("/api/agent/stream"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      history,
      attachment_ids: attachmentIds,
    }),
    signal,
  });

  if (!response.ok) {
    const text = await response.text();
    let payload: unknown = null;
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        payload = text;
      }
    }
    throw normalizeError(response, payload);
  }

  if (!response.body) {
    throw {
      status: 0,
      message: "Streaming response has no body",
    };
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line, so we parse buffered chunks accordingly.
    let boundaryIndex = buffer.indexOf("\n\n");
    while (boundaryIndex !== -1) {
      const block = buffer.slice(0, boundaryIndex);
      buffer = buffer.slice(boundaryIndex + 2);
      boundaryIndex = buffer.indexOf("\n\n");

      const parsed = parseSseBlock(block);
      if (!parsed?.data) {
        continue;
      }

      // Event data arrives as JSON; parse + validate before notifying.
      const payload = JSON.parse(parsed.data);
      const result = streamEventSchema.safeParse(payload);
      if (result.success) {
        onEvent(result.data);
      }
    }
  }

  if (buffer.trim()) {
    const parsed = parseSseBlock(buffer);
    if (parsed?.data) {
      const payload = JSON.parse(parsed.data);
      const result = streamEventSchema.safeParse(payload);
      if (result.success) {
        onEvent(result.data);
      }
    }
  }
}
