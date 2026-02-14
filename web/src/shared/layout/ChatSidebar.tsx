import { ChevronDown, ExternalLink, Plus, Settings } from "lucide-react";
import type {
  ChatAction,
  ChatItem,
  NavItem,
} from "@/features/chat/model/types";
import { cn } from "@/shared/lib/utils";
import { Avatar, AvatarFallback } from "@/shared/ui/avatar";
import { Button } from "@/shared/ui/button";
import { ScrollArea } from "@/shared/ui/scroll-area";
import { Separator } from "@/shared/ui/separator";
import { ChatConversationsList } from "./ChatConversationsList";

const iconClass = "size-[18px]";

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

  const handleToggleChats = () => {
    onToggleChats();
    if (chatMenuOpenId) {
      onChatMenuOpenChange(null);
    }
  };

  return (
    <aside
      id="app-shell-sidebar"
      className={cn(
        "fixed left-0 top-0 z-[100] flex h-screen w-[280px] -translate-x-full flex-col border-r border-marketing-border bg-marketing-sidebar-bg shadow-marketing-drawer transition-[transform,width] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] md:static md:h-auto md:translate-x-0 md:shadow-none",
        isOpen && "translate-x-0",
        !isOpen &&
          "md:-translate-x-full md:w-0 md:border-r-0 md:overflow-hidden md:shadow-marketing-drawer",
      )}
    >
      <div className="flex items-center gap-3 border-b border-marketing-border px-6 py-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-marketing-primary text-sm font-bold text-marketing-on-primary shadow-marketing-soft">
          M
        </div>
        <div className="text-lg font-bold tracking-[-0.02em] text-marketing-text-primary">
          Marketing AI
        </div>
      </div>

      <ScrollArea className="min-h-0 flex-1 px-4 py-5">
        <div className="space-y-6 pb-5">
          <div>
            <Button
              type="button"
              className={cn(
                "mb-5 h-10 w-full justify-center rounded-md border-0 bg-marketing-primary px-3 text-sm font-semibold text-marketing-on-primary shadow-marketing-soft transition-all",
                "hover:-translate-y-0.5 hover:bg-marketing-secondary hover:shadow-marketing-hover",
              )}
              onClick={onNewChat}
            >
              <Plus className={iconClass} aria-hidden="true" />
              New Chat
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="w-full flex-1 justify-between px-2 py-0 text-[0.7rem] font-bold uppercase tracking-[0.08em] text-marketing-text-muted hover:bg-transparent hover:text-marketing-text-muted"
              onClick={handleToggleChats}
              aria-expanded={chatsOpen}
              aria-controls={chatPanelId}
            >
              <span>Active Workspaces</span>
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
                <ChatConversationsList
                  chatsOpen={chatsOpen}
                  chatItems={chatItems}
                  activeChatId={activeChatId}
                  onChatSelect={onChatSelect}
                  onChatAction={onChatAction}
                  chatMenuOpenId={chatMenuOpenId}
                  onChatMenuOpenChange={onChatMenuOpenChange}
                />
              </div>
            </div>
          </div>

          <div>
            <div className="mb-2 pl-2 text-[0.7rem] font-bold uppercase tracking-[0.08em] text-marketing-text-muted">
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
                        "h-auto w-full justify-start gap-2.5 rounded-md px-3 py-2 text-[0.875rem] font-medium text-marketing-text-secondary",
                        !isActive &&
                          "hover:bg-marketing-accent-medium hover:text-marketing-text-primary",
                        isActive &&
                          "bg-marketing-accent-soft font-semibold text-marketing-primary",
                      )}
                      onClick={() => onToolSelect(tool.id)}
                    >
                      <span className="flex w-6 justify-center">
                        <Icon className={iconClass} aria-hidden="true" />
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <span>{tool.label}</span>
                        {tool.id === "phoenix" ? (
                          <ExternalLink
                            className="size-[12px] text-marketing-text-muted"
                            aria-hidden="true"
                          />
                        ) : null}
                      </span>
                    </Button>
                  </li>
                );
              })}
            </ul>
          </div>

          <div>
            <div className="mb-2 pl-2 text-[0.7rem] font-bold uppercase tracking-[0.08em] text-marketing-text-muted">
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
                        "h-auto w-full justify-start gap-2.5 rounded-md px-3 py-2 text-[0.875rem] font-medium text-marketing-text-secondary",
                        !isActive &&
                          "hover:bg-marketing-accent-medium hover:text-marketing-text-primary",
                        isActive &&
                          "bg-marketing-accent-soft font-semibold text-marketing-primary",
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
        className="m-4 h-auto w-auto justify-start gap-3 rounded-md border border-transparent bg-marketing-sidebar-bg px-2.5 py-2 text-left text-marketing-text-primary hover:border-marketing-border hover:bg-marketing-accent-medium"
      >
        <Avatar className="size-7">
          <AvatarFallback className="border border-marketing-border bg-marketing-surface text-xs font-semibold text-marketing-text-secondary">
            JD
          </AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <div className="text-[0.8rem] font-semibold">John Doe</div>
          <div className="text-[0.7rem] text-marketing-text-muted">
            Marketing Manager
          </div>
        </div>
        <Settings
          className="size-4 text-marketing-text-muted"
          aria-hidden="true"
        />
      </Button>
    </aside>
  );
}
