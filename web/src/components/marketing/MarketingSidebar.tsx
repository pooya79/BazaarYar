import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { ChatAction, ChatItem, ChatStatus, NavItem } from "./types";
import {
  ChevronDown,
  MessageSquare,
  MoreHorizontal,
  PencilLine,
  Rocket,
  Settings,
  Star,
  Trash2,
} from "lucide-react";

const iconClass = "size-[18px]";
const iconSmallClass = "size-[14px]";
const gradientClass =
  "bg-gradient-to-br from-[var(--marketing-gradient-from)] to-[var(--marketing-gradient-to)]";
const menuItemClass = "cursor-pointer rounded-lg px-2.5 py-2";

const statusClasses: Record<ChatStatus, string> = {
  active: "bg-[var(--marketing-status-active)]",
  draft: "bg-[var(--marketing-status-draft)]",
};

type MarketingSidebarProps = {
  isOpen: boolean;
  chatsOpen: boolean;
  onToggleChats: () => void;
  chatItems: ChatItem[];
  activeChatId: string | null;
  onChatSelect: (chatId: string) => void;
  onChatAction: (action: ChatAction, chatId: string) => void;
  chatMenuOpenId: string | null;
  onChatMenuOpenChange: (chatId: string | null) => void;
  tools: NavItem[];
  library: NavItem[];
  activeTool: string;
  onToolSelect: (toolId: string) => void;
};

export function MarketingSidebar({
  isOpen,
  chatsOpen,
  onToggleChats,
  chatItems,
  activeChatId,
  onChatSelect,
  onChatAction,
  chatMenuOpenId,
  onChatMenuOpenChange,
  tools,
  library,
  activeTool,
  onToolSelect,
}: MarketingSidebarProps) {
  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-[100] flex h-screen w-[300px] -translate-x-full flex-col border-r border-[var(--marketing-border)] bg-[var(--marketing-sidebar-bg)] p-6 shadow-[var(--marketing-shadow-drawer)] transition-[transform,width,padding] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] md:static md:h-auto md:translate-x-0 md:shadow-none",
        isOpen && "translate-x-0",
        !isOpen &&
          "md:-translate-x-full md:w-0 md:px-0 md:border-r-0 md:overflow-hidden md:shadow-[var(--marketing-shadow-drawer)]"
      )}
    >
      <div className="flex items-center gap-3 pb-6">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-xl text-[var(--marketing-on-primary)] shadow-[var(--marketing-shadow-soft)]",
            gradientClass
          )}
        >
          <Rocket className={iconClass} aria-hidden="true" />
        </div>
        <div className="text-xl font-bold tracking-[-0.5px] text-[var(--marketing-text-primary)]">
          Marketing AI
        </div>
      </div>
      <Separator className="bg-[var(--marketing-border)]" />

      <ScrollArea className="mt-6 min-h-0 flex-1 pr-2">
        <div className="space-y-7 pb-6">
          <div>
            <Button
              type="button"
              variant="ghost"
              className="w-full justify-between px-2 py-0 text-xs font-bold uppercase tracking-[1.2px] text-[var(--marketing-text-secondary)] hover:bg-transparent hover:text-[var(--marketing-text-secondary)]"
              onClick={onToggleChats}
              aria-expanded={chatsOpen}
            >
              <span>Chats</span>
              <ChevronDown
                className={cn(
                  iconClass,
                  "transition-transform duration-200",
                  chatsOpen && "rotate-180"
                )}
                aria-hidden="true"
              />
            </Button>
            {chatsOpen && (
              <div className="mt-3 flex flex-col gap-2">
                {chatItems.map((chat) => {
                  const isActive = activeChatId === chat.id;
                  return (
                    <div
                      key={chat.id}
                      className={cn(
                        "relative flex items-start gap-2 rounded-[10px] border border-[var(--marketing-border)] bg-[var(--marketing-surface)] py-2.5 pr-2 pl-3 transition-all duration-200",
                        !isActive &&
                          "hover:border-[var(--marketing-secondary)] hover:shadow-[var(--marketing-shadow-soft)]",
                        isActive &&
                          "border-[var(--marketing-primary)] shadow-[0_0_0_1px_var(--marketing-accent-ring)]"
                      )}
                    >
                      <Button
                        type="button"
                        variant="ghost"
                        className="h-auto flex-1 items-start justify-start px-0 py-0 text-left text-[var(--marketing-text-primary)] hover:bg-transparent hover:text-[var(--marketing-text-primary)]"
                        onClick={() => onChatSelect(chat.id)}
                      >
                        <div className="flex flex-col gap-1">
                          <div className="flex items-center gap-2 text-[0.9rem] font-semibold">
                            <span>{chat.title}</span>
                            {chat.starred && (
                              <Star
                                className={cn(
                                  iconSmallClass,
                                  "fill-current text-[var(--marketing-secondary)]"
                                )}
                                aria-hidden="true"
                              />
                            )}
                          </div>
                          <div className="flex items-center gap-2 text-xs text-[var(--marketing-text-muted)]">
                            <span
                              className={cn(
                                "inline-block h-1.5 w-1.5 rounded-full",
                                statusClasses[chat.status]
                              )}
                            />
                            <span>{chat.meta}</span>
                          </div>
                        </div>
                      </Button>
                      <DropdownMenu
                        open={chatMenuOpenId === chat.id}
                        onOpenChange={(open) =>
                          onChatMenuOpenChange(open ? chat.id : null)
                        }
                      >
                        <DropdownMenuTrigger asChild>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 rounded-lg text-[var(--marketing-text-muted)] hover:bg-[var(--marketing-accent-medium)] hover:text-[var(--marketing-primary)]"
                            aria-label="Chat options"
                          >
                            <MoreHorizontal className={iconClass} aria-hidden="true" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent
                          sideOffset={8}
                          className="min-w-[140px] rounded-[10px] border-[var(--marketing-border)] bg-[var(--marketing-surface)] p-1.5 text-[var(--marketing-text-primary)] shadow-[var(--marketing-shadow-soft)]"
                        >
                          <DropdownMenuItem
                            className={cn(
                              menuItemClass,
                              "focus:bg-[var(--marketing-accent-soft)] focus:text-[var(--marketing-primary)]"
                            )}
                            onSelect={() => onChatAction("use", chat.id)}
                          >
                            <MessageSquare
                              className={cn(
                                iconClass,
                                "text-[var(--marketing-text-primary)]"
                              )}
                              aria-hidden="true"
                            />
                            <span>Use</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className={cn(
                              menuItemClass,
                              "focus:bg-[var(--marketing-accent-soft)] focus:text-[var(--marketing-primary)]"
                            )}
                            onSelect={() => onChatAction("rename", chat.id)}
                          >
                            <PencilLine
                              className={cn(
                                iconClass,
                                "text-[var(--marketing-text-primary)]"
                              )}
                              aria-hidden="true"
                            />
                            <span>Rename</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className={cn(
                              menuItemClass,
                              "focus:bg-[var(--marketing-accent-soft)] focus:text-[var(--marketing-primary)]"
                            )}
                            onSelect={() => onChatAction("star", chat.id)}
                          >
                            <Star
                              className={cn(
                                iconClass,
                                "text-[var(--marketing-text-primary)]"
                              )}
                              aria-hidden="true"
                            />
                            <span>{chat.starred ? "Unstar" : "Star"}</span>
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            variant="destructive"
                            className={cn(
                              menuItemClass,
                              "focus:bg-[var(--marketing-danger-soft)] focus:text-[var(--marketing-danger)]"
                            )}
                            onSelect={() => onChatAction("delete", chat.id)}
                          >
                            <Trash2
                              className={cn(
                                iconClass,
                                "text-[var(--marketing-danger)]"
                              )}
                              aria-hidden="true"
                            />
                            <span>Delete</span>
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div>
            <div className="mb-3 pl-2 text-xs font-bold uppercase tracking-[1.2px] text-[var(--marketing-text-secondary)]">
              Tools
            </div>
            <ul className="space-y-1">
              {tools.map((tool) => {
                const Icon = tool.icon;
                const isActive = activeTool === tool.id;
                return (
                  <li key={tool.id}>
                    <Button
                      type="button"
                      variant="ghost"
                      className={cn(
                        "w-full justify-start gap-2.5 rounded-lg px-3 py-2.5 text-[0.9rem] font-medium text-[var(--marketing-text-secondary)]",
                        !isActive &&
                          "hover:bg-[var(--marketing-accent-soft)] hover:text-[var(--marketing-primary)]",
                        isActive &&
                          "bg-[var(--marketing-accent-strong)] font-semibold text-[var(--marketing-primary)]"
                      )}
                      onClick={() => onToolSelect(tool.id)}
                    >
                      <span className="flex w-6 justify-center">
                        <Icon className={iconClass} aria-hidden="true" />
                      </span>
                      <span>{tool.label}</span>
                    </Button>
                  </li>
                );
              })}
            </ul>
          </div>

          <div>
            <div className="mb-3 pl-2 text-xs font-bold uppercase tracking-[1.2px] text-[var(--marketing-text-secondary)]">
              Library
            </div>
            <ul className="space-y-1">
              {library.map((item) => {
                const Icon = item.icon;
                const isActive = activeTool === item.id;
                return (
                  <li key={item.id}>
                    <Button
                      type="button"
                      variant="ghost"
                      className={cn(
                        "w-full justify-start gap-2.5 rounded-lg px-3 py-2.5 text-[0.9rem] font-medium text-[var(--marketing-text-secondary)]",
                        !isActive &&
                          "hover:bg-[var(--marketing-accent-soft)] hover:text-[var(--marketing-primary)]",
                        isActive &&
                          "bg-[var(--marketing-accent-strong)] font-semibold text-[var(--marketing-primary)]"
                      )}
                      onClick={() => onToolSelect(item.id)}
                    >
                      <span className="flex w-6 justify-center">
                        <Icon className={iconClass} aria-hidden="true" />
                      </span>
                      <span>{item.label}</span>
                    </Button>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      </ScrollArea>

      <Separator className="bg-[var(--marketing-border)]" />
      <Button
        type="button"
        variant="ghost"
        className="mt-5 h-auto w-full justify-start gap-3 rounded-[10px] px-3 py-2.5 text-left text-[var(--marketing-text-primary)] hover:bg-[var(--marketing-accent-soft)]"
      >
        <Avatar className="size-9">
          <AvatarFallback
            className={cn(
              "text-[var(--marketing-on-primary)]",
              gradientClass
            )}
          >
            JD
          </AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <div className="text-[0.9rem] font-semibold">John Doe</div>
          <div className="text-xs text-[var(--marketing-text-muted)]">
            Marketing Manager
          </div>
        </div>
        <Settings className={iconClass} aria-hidden="true" />
      </Button>
    </aside>
  );
}
