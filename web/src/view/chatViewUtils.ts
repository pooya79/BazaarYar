import type {
  AssistantTurn,
  ChatTimelineItem,
  MessageAttachment,
  ToolCallEntry,
} from "@/components/chat-interface/types";
import type {
  ConversationSummary,
  PersistedMessage,
} from "@/lib/api/clients/agent.client";

export function formatTime(date: Date) {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function summarizeConversationMeta(conversation: ConversationSummary) {
  const countPart =
    conversation.messageCount === 1
      ? "1 message"
      : `${conversation.messageCount} messages`;
  const lastUpdated = conversation.lastMessageAt || conversation.updatedAt;
  const updatedPart = lastUpdated
    ? new Date(lastUpdated).toLocaleDateString()
    : "No activity";
  return `${countPart} - ${updatedPart}`;
}

export function formatMetaBlock(label: string, payload: unknown) {
  if (payload === null || payload === undefined) {
    return "";
  }
  if (typeof payload === "string") {
    return `${label}\n${payload}`;
  }
  try {
    return `${label}\n${JSON.stringify(payload, null, 2)}`;
  } catch {
    return `${label}\n${String(payload)}`;
  }
}

export function formatSandboxStatus(event: {
  run_id: string;
  stage: string;
  message: string;
}) {
  return `sandbox ${event.run_id} | ${event.stage}\n${event.message}`;
}

type ParsedMetaBlock = {
  label: string;
  payload: unknown;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function appendTextBlock(existing: string, nextValue: string) {
  const trimmed = nextValue.trim();
  if (!trimmed) {
    return existing;
  }
  if (!existing.trim()) {
    return trimmed;
  }
  return `${existing}\n\n${trimmed}`;
}

function mapPersistedAttachment(
  attachment: PersistedMessage["attachments"][number],
): MessageAttachment {
  return {
    id: attachment.id,
    filename: attachment.filename,
    contentType: attachment.contentType,
    mediaType: attachment.mediaType,
    sizeBytes: attachment.sizeBytes,
    previewText: attachment.previewText,
    extractionNote: attachment.extractionNote,
    localPreviewUrl:
      attachment.mediaType === "image" ? attachment.downloadUrl : undefined,
  };
}

function mergeAttachments(
  existing: MessageAttachment[],
  incoming: MessageAttachment[],
) {
  if (incoming.length === 0) {
    return existing;
  }
  const byId = new Map(
    existing.map((attachment) => [attachment.id, attachment]),
  );
  for (const attachment of incoming) {
    byId.set(attachment.id, attachment);
  }
  return Array.from(byId.values());
}

function parseMetaBlock(text: string): ParsedMetaBlock | null {
  const firstBreak = text.indexOf("\n");
  if (firstBreak < 0) {
    return null;
  }
  const label = text.slice(0, firstBreak).trim();
  const payloadText = text.slice(firstBreak + 1).trim();
  if (!payloadText) {
    return { label, payload: "" };
  }
  try {
    return { label, payload: JSON.parse(payloadText) };
  } catch {
    return { label, payload: payloadText };
  }
}

function readPrefixedValue(
  lines: string[],
  prefix: "name:" | "call_type:" | "id:" | "tool_call_id:",
) {
  for (const line of lines) {
    if (line.startsWith(prefix)) {
      return line.slice(prefix.length).trim();
    }
  }
  return null;
}

function parsePersistedToolCall(
  message: PersistedMessage,
  turnId: string,
): ToolCallEntry {
  const lines = message.content.split(/\r?\n/);
  const argsLineIndex = lines.findIndex((line) => line.trim() === "args:");
  const headerLines =
    argsLineIndex >= 0 ? lines.slice(0, argsLineIndex) : lines.slice();
  const streamedArgsText =
    argsLineIndex >= 0
      ? lines
          .slice(argsLineIndex + 1)
          .join("\n")
          .trim()
      : "";

  let finalArgs: Record<string, unknown> | null | undefined;
  if (streamedArgsText) {
    try {
      const parsed = JSON.parse(streamedArgsText);
      if (isRecord(parsed)) {
        finalArgs = parsed;
      }
    } catch {
      // Keep args as plain streamed text when not valid JSON.
    }
  }

  const callId = readPrefixedValue(headerLines, "id:");
  const name = readPrefixedValue(headerLines, "name:") || "unknown";

  return {
    key: callId ? `${turnId}:call:${callId}` : `${turnId}:tool:${message.id}`,
    name,
    callType: readPrefixedValue(headerLines, "call_type:"),
    callId,
    streamedArgsText,
    finalArgs,
    status: "called",
  };
}

function parsePersistedToolResult(content: string) {
  const lines = content.split(/\r?\n/);
  const firstLine = lines[0]?.trim() ?? "";
  if (firstLine.startsWith("tool_call_id:")) {
    return {
      toolCallId: firstLine.slice("tool_call_id:".length).trim() || null,
      resultContent: lines.slice(1).join("\n").trim(),
    };
  }
  return { toolCallId: null, resultContent: content.trim() };
}

function createAssistantTurn(id: string, time: string): AssistantTurn {
  return {
    id,
    sender: "assistant",
    time,
    answerText: "",
    reasoningText: "",
    notes: [],
    toolCalls: [],
    attachments: [],
    usage: null,
    responseMetadata: null,
    reasoningTokens: null,
  };
}

function attachResultToTurn(
  turn: AssistantTurn,
  {
    toolCallId,
    resultContent,
    artifacts,
    fallbackKey,
  }: {
    toolCallId: string | null;
    resultContent: string;
    artifacts: MessageAttachment[];
    fallbackKey: string;
  },
) {
  const toolCalls = turn.toolCalls.slice();
  let targetIndex = -1;

  if (toolCallId) {
    targetIndex = toolCalls.findIndex((item) => item.callId === toolCallId);
  }
  if (targetIndex < 0) {
    targetIndex = toolCalls.findIndex((item) => !item.resultContent);
  }
  if (targetIndex < 0) {
    toolCalls.push({
      key: toolCallId
        ? `${turn.id}:result:${toolCallId}`
        : `${turn.id}:result:${fallbackKey}`,
      name: "unknown",
      callId: toolCallId,
      streamedArgsText: "",
      status: "called",
    });
    targetIndex = toolCalls.length - 1;
  }

  const current = toolCalls[targetIndex];
  toolCalls[targetIndex] = {
    ...current,
    callId: current.callId || toolCallId,
    resultContent,
    resultArtifacts: artifacts,
    status: "completed",
  };

  return {
    ...turn,
    toolCalls,
    attachments: mergeAttachments(turn.attachments, artifacts),
  };
}

export function extractReasoningTokens(
  usage: Record<string, unknown> | null | undefined,
) {
  if (!usage) {
    return null;
  }

  const topLevel = usage.reasoning_tokens;
  if (typeof topLevel === "number") {
    return topLevel;
  }

  for (const key of [
    "output_token_details",
    "completion_token_details",
    "completion_tokens_details",
  ]) {
    const details = usage[key];
    if (isRecord(details) && typeof details.reasoning_tokens === "number") {
      return details.reasoning_tokens;
    }
  }

  return null;
}

export function groupConversationMessages(
  messages: PersistedMessage[],
): ChatTimelineItem[] {
  const timeline: ChatTimelineItem[] = [];
  const sortedMessages = messages
    .slice()
    .sort(
      (a, b) =>
        new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
    );

  let activeTurn: AssistantTurn | null = null;

  for (const message of sortedMessages) {
    const time = formatTime(new Date(message.createdAt));
    const mappedAttachments = message.attachments
      .slice()
      .sort((a, b) => a.position - b.position)
      .map(mapPersistedAttachment);

    if (message.role === "user") {
      activeTurn = null;
      timeline.push({
        id: `user:${message.id}`,
        sender: "user",
        text: message.content,
        time,
        attachments:
          mappedAttachments.length > 0 ? mappedAttachments : undefined,
      });
      continue;
    }

    if (!activeTurn) {
      activeTurn = createAssistantTurn(`assistant:${message.id}`, time);
      timeline.push(activeTurn);
    }

    activeTurn.time = time;
    if (mappedAttachments.length > 0) {
      activeTurn.attachments = mergeAttachments(
        activeTurn.attachments,
        mappedAttachments,
      );
    }

    if (message.usageJson) {
      activeTurn.usage = message.usageJson;
      activeTurn.reasoningTokens = extractReasoningTokens(message.usageJson);
    }

    if (message.messageKind === "normal") {
      activeTurn.answerText = appendTextBlock(
        activeTurn.answerText,
        message.content,
      );
      continue;
    }

    if (message.messageKind === "summary") {
      activeTurn.notes = [...activeTurn.notes, `summary\n${message.content}`];
      continue;
    }

    if (message.messageKind === "tool_call") {
      const parsed = parsePersistedToolCall(message, activeTurn.id);
      const existingIndex = parsed.callId
        ? activeTurn.toolCalls.findIndex(
            (item) => item.callId === parsed.callId,
          )
        : -1;
      if (existingIndex >= 0) {
        const next = activeTurn.toolCalls.slice();
        next[existingIndex] = { ...next[existingIndex], ...parsed };
        activeTurn.toolCalls = next;
      } else {
        activeTurn.toolCalls = [...activeTurn.toolCalls, parsed];
      }
      continue;
    }

    if (message.messageKind === "tool_result") {
      const parsed = parsePersistedToolResult(message.content);
      activeTurn = attachResultToTurn(activeTurn, {
        toolCallId: parsed.toolCallId,
        resultContent: parsed.resultContent,
        artifacts: mappedAttachments,
        fallbackKey: message.id,
      });
      timeline[timeline.length - 1] = activeTurn;
      continue;
    }

    if (message.messageKind === "meta") {
      const parsed = parseMetaBlock(message.content);
      if (parsed?.label === "usage" && isRecord(parsed.payload)) {
        activeTurn.usage = parsed.payload;
        activeTurn.reasoningTokens = extractReasoningTokens(parsed.payload);
        continue;
      }
      if (parsed?.label === "response_metadata" && isRecord(parsed.payload)) {
        activeTurn.responseMetadata = parsed.payload;
        continue;
      }
      activeTurn.notes = [...activeTurn.notes, message.content];
    }
  }

  return timeline;
}
