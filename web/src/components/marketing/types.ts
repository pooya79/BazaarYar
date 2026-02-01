import type { LucideIcon } from "lucide-react";

export type Message = {
  id: number;
  sender: "bot" | "user";
  text: string;
  time: string;
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
