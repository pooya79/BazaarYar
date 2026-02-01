import type { LucideIcon } from "lucide-react";

export type Sender = "bot" | "user";

export type Message = {
  id: number;
  sender: Sender;
  text: string;
  time: string;
};

export type ChatStatus = "active" | "draft";

export type ChatItem = {
  id: string;
  title: string;
  meta: string;
  status: ChatStatus;
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
