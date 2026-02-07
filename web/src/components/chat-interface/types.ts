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
};

export type Message = {
  id: number;
  sender: "bot" | "user";
  text: string;
  time: string;
  kind?: "assistant" | "reasoning" | "tool_call" | "tool_result" | "meta";
  attachments?: MessageAttachment[];
};

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

export type QuickAction = {
  title: string;
  description: string;
  icon: LucideIcon;
  prompt: string;
};
