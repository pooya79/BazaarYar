import type {
  AssistantTurn,
  ChatTimelineItem,
  MessageAttachment,
  ToolCallEntry,
} from "@/features/chat/model/types";
import type {
  ConversationSummary,
  PersistedMessage,
} from "@/shared/api/clients/agent.client";

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
    downloadUrl: attachment.downloadUrl,
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

const TOOL_RESULT_SECTION_HEADERS = [
  "input_files:",
  "artifact_attachments:",
  "stdout:",
  "stderr:",
] as const;

type ParsedFormattedToolResult = {
  toolCallId: string | null;
  status: string | null;
  summary: string | null;
  sandboxSessionId: string | null;
  sandboxReused: string | null;
  requestSequence: string | null;
  queueWaitMs: string | null;
  inputFiles: string[];
  artifactAttachments: string[];
  stdout: string | null;
  stderr: string | null;
};

export type PythonToolViewModel = {
  code: string | null;
  status: string | null;
  summary: string | null;
  sandboxSessionId: string | null;
  sandboxReused: string | null;
  requestSequence: string | null;
  queueWaitMs: string | null;
  stdout: string | null;
  stderr: string | null;
  inputFiles: string[];
  artifactAttachments: string[];
  rawResult: string;
  rawArgs: string;
  rawFinalArgs: string | null;
};

function readScalarValue(line: string, prefix: string) {
  const value = line.slice(prefix.length).trim();
  return value || null;
}

function safeStringify(value: unknown) {
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function parseJsonArgs(text: string) {
  if (!text.trim()) {
    return null;
  }
  try {
    const parsed = JSON.parse(text);
    return isRecord(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function payloadValueAsString(
  payload: Record<string, unknown> | null | undefined,
  key: string,
) {
  if (!payload) {
    return null;
  }
  const value = payload[key];
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return safeStringify(value);
}

function payloadInputFileRows(
  payload: Record<string, unknown> | null | undefined,
) {
  const input = payload?.input_files;
  if (!Array.isArray(input)) {
    return [];
  }

  const rows: string[] = [];
  for (const item of input) {
    if (!isRecord(item)) {
      rows.push(safeStringify(item));
      continue;
    }
    const originalFilename = String(item.original_filename ?? "").trim() || "-";
    const sandboxFilename =
      String(item.sandbox_filename ?? "").trim() || "[unknown]";
    const inputPath = String(item.input_path ?? "").trim() || "-";
    rows.push(
      `${sandboxFilename} (original=${originalFilename}, path=${inputPath})`,
    );
  }
  return rows;
}

function payloadArtifactRows(
  payload: Record<string, unknown> | null | undefined,
) {
  const artifacts = payload?.artifacts;
  if (!Array.isArray(artifacts)) {
    return [];
  }

  const rows: string[] = [];
  for (const item of artifacts) {
    if (!isRecord(item)) {
      rows.push(safeStringify(item));
      continue;
    }
    const filename = String(item.filename ?? "").trim() || "[unnamed]";
    const contentType = String(item.content_type ?? "").trim() || "-";
    rows.push(`${filename} (content_type=${contentType})`);
  }
  return rows;
}

export function isPythonToolCall(tool: ToolCallEntry) {
  if (tool.name === "run_python_code") {
    return true;
  }
  return typeof tool.finalArgs?.code === "string";
}

export function extractPythonCode(tool: ToolCallEntry) {
  const finalCode = tool.finalArgs?.code;
  if (typeof finalCode === "string" && finalCode.trim()) {
    return finalCode;
  }

  const parsedArgs = parseJsonArgs(tool.streamedArgsText);
  const streamedCode = parsedArgs?.code;
  if (typeof streamedCode === "string" && streamedCode.trim()) {
    return streamedCode;
  }

  return null;
}

export function parseFormattedToolResult(
  content: string,
): ParsedFormattedToolResult {
  const parsed: ParsedFormattedToolResult = {
    toolCallId: null,
    status: null,
    summary: null,
    sandboxSessionId: null,
    sandboxReused: null,
    requestSequence: null,
    queueWaitMs: null,
    inputFiles: [],
    artifactAttachments: [],
    stdout: null,
    stderr: null,
  };

  if (!content.trim()) {
    return parsed;
  }

  const lines = content.split(/\r?\n/);
  const sectionHeaders = new Set<string>(TOOL_RESULT_SECTION_HEADERS);
  const isSectionHeader = (line: string) => sectionHeaders.has(line.trim());

  let index = 0;
  while (index < lines.length) {
    const rawLine = lines[index] ?? "";
    const trimmed = rawLine.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    if (trimmed.startsWith("tool_call_id:")) {
      parsed.toolCallId = readScalarValue(trimmed, "tool_call_id:");
      index += 1;
      continue;
    }
    if (trimmed.startsWith("status:")) {
      parsed.status = readScalarValue(trimmed, "status:");
      index += 1;
      continue;
    }
    if (trimmed.startsWith("summary:")) {
      parsed.summary = readScalarValue(trimmed, "summary:");
      index += 1;
      continue;
    }
    if (trimmed.startsWith("sandbox_session_id:")) {
      parsed.sandboxSessionId = readScalarValue(trimmed, "sandbox_session_id:");
      index += 1;
      continue;
    }
    if (trimmed.startsWith("sandbox_reused:")) {
      parsed.sandboxReused = readScalarValue(trimmed, "sandbox_reused:");
      index += 1;
      continue;
    }
    if (trimmed.startsWith("request_sequence:")) {
      parsed.requestSequence = readScalarValue(trimmed, "request_sequence:");
      index += 1;
      continue;
    }
    if (trimmed.startsWith("queue_wait_ms:")) {
      parsed.queueWaitMs = readScalarValue(trimmed, "queue_wait_ms:");
      index += 1;
      continue;
    }

    if (
      trimmed === "input_files:" ||
      trimmed === "artifact_attachments:" ||
      trimmed === "stdout:" ||
      trimmed === "stderr:"
    ) {
      const section = trimmed.slice(0, -1);
      index += 1;
      const body: string[] = [];
      while (index < lines.length) {
        const candidate = lines[index] ?? "";
        if (isSectionHeader(candidate)) {
          break;
        }
        body.push(candidate);
        index += 1;
      }

      if (section === "input_files") {
        parsed.inputFiles = body
          .map((line) => line.trim())
          .filter(Boolean)
          .map((line) => (line.startsWith("- ") ? line.slice(2) : line));
      } else if (section === "artifact_attachments") {
        parsed.artifactAttachments = body
          .map((line) => line.trim())
          .filter(Boolean)
          .map((line) => (line.startsWith("- ") ? line.slice(2) : line));
      } else if (section === "stdout") {
        const text = body.join("\n").trim();
        parsed.stdout = text || null;
      } else if (section === "stderr") {
        const text = body.join("\n").trim();
        parsed.stderr = text || null;
      }
      continue;
    }

    index += 1;
  }

  return parsed;
}

export function buildPythonToolViewModel(
  tool: ToolCallEntry,
): PythonToolViewModel {
  const fallback = parseFormattedToolResult(tool.resultContent ?? "");
  const payload = isRecord(tool.resultPayload) ? tool.resultPayload : null;
  const code = extractPythonCode(tool);
  const inputFileRows = payloadInputFileRows(payload);
  const artifactRows = payloadArtifactRows(payload);

  const payloadStdout = payloadValueAsString(payload, "stdout_tail");
  const payloadStderr = payloadValueAsString(payload, "stderr_tail");

  return {
    code,
    status: payloadValueAsString(payload, "status") ?? fallback.status,
    summary: payloadValueAsString(payload, "summary") ?? fallback.summary,
    sandboxSessionId:
      payloadValueAsString(payload, "sandbox_session_id") ??
      fallback.sandboxSessionId,
    sandboxReused:
      payloadValueAsString(payload, "sandbox_reused") ?? fallback.sandboxReused,
    requestSequence:
      payloadValueAsString(payload, "request_sequence") ??
      fallback.requestSequence,
    queueWaitMs:
      payloadValueAsString(payload, "queue_wait_ms") ?? fallback.queueWaitMs,
    stdout: payloadStdout ?? fallback.stdout,
    stderr: payloadStderr ?? fallback.stderr,
    inputFiles: inputFileRows.length > 0 ? inputFileRows : fallback.inputFiles,
    artifactAttachments:
      artifactRows.length > 0 ? artifactRows : fallback.artifactAttachments,
    rawResult: tool.resultContent ?? "",
    rawArgs: tool.streamedArgsText,
    rawFinalArgs: tool.finalArgs
      ? JSON.stringify(tool.finalArgs, null, 2)
      : null,
  };
}

function createAssistantTurn(id: string, time: string): AssistantTurn {
  return {
    id,
    sender: "assistant",
    time,
    blocks: [],
    toolCalls: [],
    attachments: [],
    usage: null,
    responseMetadata: null,
    reasoningTokens: null,
  };
}

function withToolBlock(
  turn: AssistantTurn,
  {
    toolKey,
    sourceId,
  }: {
    toolKey: string;
    sourceId: string;
  },
): AssistantTurn {
  if (
    turn.blocks.some(
      (block) => block.type === "tool_call" && block.toolKey === toolKey,
    )
  ) {
    return turn;
  }

  return {
    ...turn,
    blocks: [
      ...turn.blocks,
      {
        id: `${turn.id}:block:tool:${sourceId}`,
        type: "tool_call",
        toolKey,
      },
    ],
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

  let updated = {
    ...turn,
    toolCalls,
    attachments: mergeAttachments(turn.attachments, artifacts),
  };

  updated = withToolBlock(updated, {
    toolKey: toolCalls[targetIndex].key,
    sourceId: fallbackKey,
  });

  return updated;
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
  const sortedMessages = messages.slice().sort((a, b) => {
    const createdDelta =
      new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
    if (createdDelta !== 0) {
      return createdDelta;
    }
    return a.id.localeCompare(b.id);
  });

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

    if (typeof message.reasoningTokens === "number") {
      activeTurn.reasoningTokens = message.reasoningTokens;
    }
    if (message.usageJson) {
      activeTurn.usage = message.usageJson;
      if (activeTurn.reasoningTokens === null) {
        activeTurn.reasoningTokens = extractReasoningTokens(message.usageJson);
      }
    }

    if (message.messageKind === "normal") {
      activeTurn.blocks = [
        ...activeTurn.blocks,
        {
          id: `${activeTurn.id}:block:text:${message.id}`,
          type: "text",
          content: message.content,
        },
      ];
      continue;
    }

    if (message.messageKind === "reasoning") {
      activeTurn.blocks = [
        ...activeTurn.blocks,
        {
          id: `${activeTurn.id}:block:reasoning:${message.id}`,
          type: "reasoning",
          content: message.content,
        },
      ];
      continue;
    }

    if (message.messageKind === "summary") {
      activeTurn.blocks = [
        ...activeTurn.blocks,
        {
          id: `${activeTurn.id}:block:note:summary:${message.id}`,
          type: "note",
          content: `summary\n${message.content}`,
        },
      ];
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
        activeTurn = withToolBlock(activeTurn, {
          toolKey: next[existingIndex].key,
          sourceId: message.id,
        });
      } else {
        activeTurn.toolCalls = [...activeTurn.toolCalls, parsed];
        activeTurn = withToolBlock(activeTurn, {
          toolKey: parsed.key,
          sourceId: message.id,
        });
      }
      timeline[timeline.length - 1] = activeTurn;
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
        if (activeTurn.reasoningTokens === null) {
          activeTurn.reasoningTokens = extractReasoningTokens(parsed.payload);
        }
        continue;
      }
      if (parsed?.label === "response_metadata" && isRecord(parsed.payload)) {
        activeTurn.responseMetadata = parsed.payload;
        continue;
      }
      if (parsed?.label === "reasoning") {
        const reasoningText =
          typeof parsed.payload === "string"
            ? parsed.payload
            : JSON.stringify(parsed.payload, null, 2);
        activeTurn.blocks = [
          ...activeTurn.blocks,
          {
            id: `${activeTurn.id}:block:reasoning:meta:${message.id}`,
            type: "reasoning",
            content: reasoningText,
          },
        ];
        continue;
      }
      activeTurn.blocks = [
        ...activeTurn.blocks,
        {
          id: `${activeTurn.id}:block:note:meta:${message.id}`,
          type: "note",
          content: message.content,
        },
      ];
    }
  }

  return timeline;
}
