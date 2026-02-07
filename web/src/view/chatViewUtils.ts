import type { Message } from "@/components/chat-interface/types";
import type { ConversationSummary } from "@/lib/api/clients/agent.client";

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

export function mapConversationKind(
  kind: "normal" | "summary" | "meta" | "tool_call" | "tool_result",
): Message["kind"] {
  if (kind === "normal") {
    return "assistant";
  }
  if (kind === "summary") {
    return "summary";
  }
  return kind;
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

export function formatToolDelta(entry: {
  name?: string;
  args?: string;
  callId?: string;
}) {
  const headerParts = [`name: ${entry.name ?? "unknown"}`];
  if (entry.callId) {
    headerParts.push(`id: ${entry.callId}`);
  }
  const header = headerParts.join(" | ");
  return entry.args ? `${header}\n${entry.args}` : header;
}

export function formatToolCall(event: {
  name?: string | null;
  id?: string | null;
  call_type?: string | null;
  args?: Record<string, unknown>;
}) {
  const lines = [`name: ${event.name ?? "unknown"}`];
  if (event.call_type) {
    lines.push(`call_type: ${event.call_type}`);
  }
  if (event.id) {
    lines.push(`id: ${event.id}`);
  }
  if (event.args) {
    lines.push("args:");
    lines.push(JSON.stringify(event.args, null, 2));
  }
  return lines.join("\n");
}

export function formatToolResult(event: {
  tool_call_id?: string | null;
  content: string;
}) {
  const lines: string[] = [];
  if (event.tool_call_id) {
    lines.push(`tool_call_id: ${event.tool_call_id}`);
  }
  lines.push(event.content);
  return lines.join("\n");
}
