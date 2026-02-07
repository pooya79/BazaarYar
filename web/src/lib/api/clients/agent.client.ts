import { buildUrl, normalizeError } from "../http";
import {
  contextWindowSchema,
  conversationDetailSchema,
  conversationSummarySchema,
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

export type ConversationSummary = {
  id: string;
  title?: string | null;
  starred: boolean;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  lastMessageAt?: string | null;
};

export type PersistedAttachment = UploadedAttachment & {
  position: number;
  downloadUrl: string;
};

export type PersistedMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  tokenEstimate: number;
  tokenizerName?: string | null;
  messageKind: "normal" | "summary" | "meta" | "tool_call" | "tool_result";
  archivedAt?: string | null;
  usageJson?: Record<string, unknown> | null;
  createdAt: string;
  attachments: PersistedAttachment[];
};

export type ConversationDetail = {
  id: string;
  title?: string | null;
  starred: boolean;
  createdAt: string;
  updatedAt: string;
  messages: PersistedMessage[];
};

export type ContextWindow = {
  conversationId: string;
  maxTokens: number;
  targetTokens: number;
  keepLastTurns: number;
  tokenSum: number;
  messages: PersistedMessage[];
};

export type StreamAgentOptions = {
  message: string;
  conversationId?: string | null;
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

const mapPersistedMessage = (
  message: ReturnType<
    typeof conversationDetailSchema.parse
  >["messages"][number],
): PersistedMessage => ({
  id: message.id,
  role: message.role,
  content: message.content,
  tokenEstimate: message.token_estimate,
  tokenizerName: message.tokenizer_name,
  messageKind: message.message_kind,
  archivedAt: message.archived_at,
  usageJson: message.usage_json,
  createdAt: message.created_at,
  attachments: message.attachments.map((attachment) => ({
    id: attachment.id,
    filename: attachment.filename,
    contentType: attachment.content_type,
    mediaType: attachment.media_type,
    sizeBytes: attachment.size_bytes,
    previewText: attachment.preview_text,
    extractionNote: attachment.extraction_note,
    position: attachment.position,
    downloadUrl: buildUrl(attachment.download_url),
  })),
});

export async function listAgentConversations(
  signal?: AbortSignal,
): Promise<ConversationSummary[]> {
  const response = await fetch(buildUrl("/api/conversations"), {
    method: "GET",
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
  const parsed = conversationSummarySchema.array().parse(payload);
  return parsed.map((item) => ({
    id: item.id,
    title: item.title,
    starred: item.starred,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
    messageCount: item.message_count,
    lastMessageAt: item.last_message_at,
  }));
}

export async function getAgentConversation(
  conversationId: string,
  signal?: AbortSignal,
): Promise<ConversationDetail> {
  const response = await fetch(
    buildUrl(`/api/conversations/${conversationId}`),
    {
      method: "GET",
      signal,
    },
  );

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
  const parsed = conversationDetailSchema.parse(payload);
  return {
    id: parsed.id,
    title: parsed.title,
    starred: parsed.starred,
    createdAt: parsed.created_at,
    updatedAt: parsed.updated_at,
    messages: parsed.messages.map(mapPersistedMessage),
  };
}

async function parseSummaryResponse(
  response: Response,
): Promise<ConversationSummary> {
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
  const parsed = conversationSummarySchema.parse(payload);
  return {
    id: parsed.id,
    title: parsed.title,
    starred: parsed.starred,
    createdAt: parsed.created_at,
    updatedAt: parsed.updated_at,
    messageCount: parsed.message_count,
    lastMessageAt: parsed.last_message_at,
  };
}

export async function renameAgentConversation(
  conversationId: string,
  title: string,
  signal?: AbortSignal,
): Promise<ConversationSummary> {
  const response = await fetch(
    buildUrl(`/api/conversations/${conversationId}/title`),
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title }),
      signal,
    },
  );
  return parseSummaryResponse(response);
}

export async function starAgentConversation(
  conversationId: string,
  starred: boolean,
  signal?: AbortSignal,
): Promise<ConversationSummary> {
  const response = await fetch(
    buildUrl(`/api/conversations/${conversationId}/star`),
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ starred }),
      signal,
    },
  );
  return parseSummaryResponse(response);
}

export async function deleteAgentConversation(
  conversationId: string,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(
    buildUrl(`/api/conversations/${conversationId}`),
    {
      method: "DELETE",
      signal,
    },
  );

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
}

export async function getAgentContextWindow(
  conversationId: string,
  signal?: AbortSignal,
): Promise<ContextWindow> {
  const response = await fetch(
    buildUrl(`/api/conversations/${conversationId}/context-window`),
    {
      method: "GET",
      signal,
    },
  );

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
  const parsed = contextWindowSchema.parse(payload);
  return {
    conversationId: parsed.conversation_id,
    maxTokens: parsed.max_tokens,
    targetTokens: parsed.target_tokens,
    keepLastTurns: parsed.keep_last_turns,
    tokenSum: parsed.token_sum,
    messages: parsed.messages.map(mapPersistedMessage),
  };
}

export async function streamAgent({
  message,
  conversationId,
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
      conversation_id: conversationId,
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
