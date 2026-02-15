import type { LucideIcon } from "lucide-react";

export type MessageAttachment = {
  id: string;
  filename: string;
  contentType: string;
  mediaType: "image" | "pdf" | "text" | "spreadsheet" | "binary";
  sizeBytes: number;
  previewText?: string | null;
  extractionNote?: string | null;
  localPreviewUrl?: string;
  downloadUrl?: string;
};

export type ToolCallEntry = {
  key: string;
  name: string;
  callType?: string | null;
  callId?: string | null;
  streamedArgsText: string;
  finalArgs?: Record<string, unknown> | null;
  resultContent?: string | null;
  resultPayload?: Record<string, unknown> | null;
  resultArtifacts?: MessageAttachment[];
  status: "streaming" | "called" | "completed";
};

export type AssistantContentBlock =
  | {
      id: string;
      type: "text";
      content: string;
    }
  | {
      id: string;
      type: "reasoning";
      content: string;
    }
  | {
      id: string;
      type: "note";
      content: string;
    }
  | {
      id: string;
      type: "tool_call";
      toolKey: string;
    };

export type AssistantTurn = {
  id: string;
  sender: "assistant";
  time: string;
  blocks: AssistantContentBlock[];
  toolCalls: ToolCallEntry[];
  attachments: MessageAttachment[];
  usage?: Record<string, unknown> | null;
  responseMetadata?: Record<string, unknown> | null;
  reasoningTokens?: number | null;
};

export type UserMessage = {
  id: string;
  sender: "user";
  text: string;
  time: string;
  attachments?: MessageAttachment[];
};

export type ChatTimelineItem = UserMessage | AssistantTurn;

export type ChatItem = {
  id: string;
  title: string;
  meta: string;
  status: "active" | "draft";
  starred: boolean;
};

export type ChatAction = "use" | "rename" | "delete" | "star";

export type NavItem = {
  id: string;
  label: string;
  icon: LucideIcon;
};

export type LibrarySection = {
  id: string;
  label: string;
  items: NavItem[];
};

export type QuickAction = {
  title: string;
  description: string;
  icon: LucideIcon;
  prompt: string;
};
