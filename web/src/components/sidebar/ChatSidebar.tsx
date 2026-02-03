import {
  ChevronDown,
  MessageSquare,
  MoreHorizontal,
  PencilLine,
  Plus,
  Rocket,
  Settings,
  Star,
  Trash2,
} from "lucide-react";
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
import type { ChatAction, ChatItem, NavItem } from "@/components/chat-interface/types";

const iconClass = "size-[18px]";
const iconSmallClass = "size-[14px]";
const gradientClass =
  "bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to";
const menuItemClass = "cursor-pointer rounded-lg px-2.5 py-2";
type ChatStatus = ChatItem["status"];

const statusClasses: Record<ChatStatus, string> = {
  active: "bg-marketing-status-active",
  draft: "bg-marketing-status-draft",
};

type ChatSidebarProps = {
  isOpen: boolean;
  chatsOpen: boolean;
  onToggleChats: () => void;
  onNewChat: () => void;
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

export function ChatSidebar({
  isOpen,
  chatsOpen,
  onToggleChats,
  onNewChat,
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
}: ChatSidebarProps) {
  const chatPanelId = "chat-chats-panel";
  const chatsState = chatsOpen ? "open" : "closed";
  const hasChats = chatItems.length > 0;

  const handleToggleChats = () => {
    onToggleChats();
    if (chatMenuOpenId) {
      onChatMenuOpenChange(null);
    }
  };

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-[100] flex h-screen w-[300px] -translate-x-full flex-col border-r border-marketing-border bg-marketing-sidebar-bg p-6 shadow-marketing-drawer transition-[transform,width,padding] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] md:static md:h-auto md:translate-x-0 md:shadow-none",
        isOpen && "translate-x-0",
        !isOpen &&
          "md:-translate-x-full md:w-0 md:px-0 md:border-r-0 md:overflow-hidden md:shadow-marketing-drawer",
      )}
    >
      <div className="flex items-center gap-3 pb-6">
        <div
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-xl text-marketing-on-primary shadow-marketing-soft",
            gradientClass,
          )}
        >
          <Rocket className={iconClass} aria-hidden="true" />
        </div>
        <div className="text-xl font-bold tracking-[-0.5px] text-marketing-text-primary">
          AI Assistant
        </div>
      </div>
      <Separator className="bg-marketing-border" />

      <ScrollArea className="mt-6 min-h-0 flex-1 pr-3">
        <div className="space-y-7 pb-6">
          <div>
            <Button
              type="button"
              className={cn(
                "mb-4 w-full justify-center rounded-xl px-3 py-2 text-sm font-semibold text-marketing-on-primary shadow-marketing-soft transition-all",
                gradientClass,
                "hover:-translate-y-0.5 hover:shadow-marketing-hover",
              )}
              onClick={onNewChat}
            >
              <Plus className={iconClass} aria-hidden="true" />
              New chat
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="w-full flex-1 justify-between px-2 py-0 text-xs font-bold uppercase tracking-[1.2px] text-marketing-text-secondary hover:bg-transparent hover:text-marketing-text-secondary"
              onClick={handleToggleChats}
              aria-expanded={chatsOpen}
              aria-controls={chatPanelId}
            >
              <span>Chats</span>
              <ChevronDown
                className={cn(
                  iconClass,
                  "transition-transform duration-300",
                  chatsOpen && "rotate-180",
                )}
                aria-hidden="true"
              />
            </Button>
            <div
              id={chatPanelId}
              data-state={chatsState}
              aria-hidden={!chatsOpen}
              className={cn(
                "grid transition-[grid-template-rows] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]",
                chatsOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
              )}
            >
              <div className="overflow-hidden">
                <div
                  className={cn(
                    "mt-3 flex flex-col gap-2 transition-[opacity,transform] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]",
                    chatsOpen
                      ? "opacity-100 translate-y-0"
                      : "pointer-events-none opacity-0 -translate-y-2",
                  )}
                >
                  {!hasChats ? (
                    <div className="rounded-[10px] border border-dashed border-marketing-border bg-marketing-surface px-3 py-4 text-xs text-marketing-text-muted">
                      No chats yet. Start a conversation to see it here.
                    </div>
                  ) : (
                    chatItems.map((chat) => {
                      const isActive = activeChatId === chat.id;
                      const statusClass =
                        statusClasses[chat.status] ?? "bg-marketing-border";

                      return (
                        <div
                          key={chat.id}
                          className={cn(
                            "relative flex items-start gap-2 rounded-[10px] border border-marketing-border bg-marketing-surface py-2.5 pr-2 pl-3 transition-all duration-200",
                            !isActive &&
                              "hover:border-marketing-secondary hover:shadow-marketing-soft",
                            isActive &&
                              "border-marketing-primary ring-1 ring-marketing-accent-ring",
                          )}
                        >
                          <Button
                            type="button"
                            variant="ghost"
                            className="h-auto min-w-0 flex-1 items-start justify-start px-0 py-0 text-left text-marketing-text-primary hover:bg-transparent hover:text-marketing-text-primary"
                            onClick={() => onChatSelect(chat.id)}
                          >
                            <div className="flex min-w-0 flex-col gap-1">
                              <div className="flex min-w-0 items-center gap-2 text-[0.9rem] font-semibold">
                                <span className="truncate">{chat.title}</span>
                                {chat.starred && (
                                  <Star
                                    className={cn(
                                      iconSmallClass,
                                      "fill-current text-marketing-secondary",
                                    )}
                                    aria-hidden="true"
                                  />
                                )}
                              </div>
                              <div className="flex min-w-0 items-center gap-2 text-xs text-marketing-text-muted">
                                <span
                                  className={cn(
                                    "inline-block h-1.5 w-1.5 rounded-full",
                                    statusClass,
                                  )}
                                />
                                <span className="truncate">{chat.meta}</span>
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
                                className="h-8 w-8 rounded-lg text-marketing-text-muted hover:bg-marketing-accent-medium hover:text-marketing-primary"
                                aria-label="Chat options"
                              >
                                <MoreHorizontal
                                  className={iconClass}
                                  aria-hidden="true"
                                />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent
                              sideOffset={8}
                              className="z-[120] min-w-[140px] rounded-[10px] border-marketing-border bg-marketing-surface p-1.5 text-marketing-text-primary shadow-marketing-soft"
                            >
                              <DropdownMenuItem
                                className={cn(
                                  menuItemClass,
                                  "focus:bg-marketing-accent-soft focus:text-marketing-primary",
                                )}
                                onSelect={() => onChatAction("use", chat.id)}
                              >
                                <MessageSquare
                                  className={cn(
                                    iconClass,
                                    "text-marketing-text-primary",
                                  )}
                                  aria-hidden="true"
                                />
                                <span>Use</span>
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                className={cn(
                                  menuItemClass,
                                  "focus:bg-marketing-accent-soft focus:text-marketing-primary",
                                )}
                                onSelect={() => onChatAction("rename", chat.id)}
                              >
                                <PencilLine
                                  className={cn(
                                    iconClass,
                                    "text-marketing-text-primary",
                                  )}
                                  aria-hidden="true"
                                />
                                <span>Rename</span>
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                className={cn(
                                  menuItemClass,
                                  "focus:bg-marketing-accent-soft focus:text-marketing-primary",
                                )}
                                onSelect={() => onChatAction("star", chat.id)}
                              >
                                <Star
                                  className={cn(
                                    iconClass,
                                    "text-marketing-text-primary",
                                  )}
                                  aria-hidden="true"
                                />
                                <span>{chat.starred ? "Unstar" : "Star"}</span>
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                variant="destructive"
                                className={cn(
                                  menuItemClass,
                                  "focus:bg-marketing-danger-soft focus:text-marketing-danger",
                                )}
                                onSelect={() => onChatAction("delete", chat.id)}
                              >
                                <Trash2
                                  className={cn(
                                    iconClass,
                                    "text-marketing-danger",
                                  )}
                                  aria-hidden="true"
                                />
                                <span>Delete</span>
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          </div>

          <div>
            <div className="mb-3 pl-2 text-xs font-bold uppercase tracking-[1.2px] text-marketing-text-secondary">
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
                        "w-full justify-start gap-2.5 rounded-lg px-3 py-2.5 text-[0.9rem] font-medium text-marketing-text-secondary",
                        !isActive &&
                          "hover:bg-marketing-accent-soft hover:text-marketing-primary",
                        isActive &&
                          "bg-marketing-accent-strong font-semibold text-marketing-primary",
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
            <div className="mb-3 pl-2 text-xs font-bold uppercase tracking-[1.2px] text-marketing-text-secondary">
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
                        "w-full justify-start gap-2.5 rounded-lg px-3 py-2.5 text-[0.9rem] font-medium text-marketing-text-secondary",
                        !isActive &&
                          "hover:bg-marketing-accent-soft hover:text-marketing-primary",
                        isActive &&
                          "bg-marketing-accent-strong font-semibold text-marketing-primary",
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

      <Separator className="bg-marketing-border" />
      <Button
        type="button"
        variant="ghost"
        className="mt-5 h-auto w-full justify-start gap-3 rounded-[10px] px-3 py-2.5 text-left text-marketing-text-primary hover:bg-marketing-accent-soft"
      >
        <Avatar className="size-9">
          <AvatarFallback
            className={cn("text-marketing-on-primary", gradientClass)}
          >
            JD
          </AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <div className="text-[0.9rem] font-semibold">John Doe</div>
          <div className="text-xs text-marketing-text-muted">
            Workspace Manager
          </div>
        </div>
        <Settings className={iconClass} aria-hidden="true" />
      </Button>
    </aside>
  );
}
