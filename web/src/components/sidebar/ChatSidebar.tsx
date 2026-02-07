import { ChevronDown, Plus, Rocket, Settings } from "lucide-react";
import type {
  ChatAction,
  ChatItem,
  NavItem,
} from "@/components/chat-interface/types";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { ChatConversationsList } from "./ChatConversationsList";

const iconClass = "size-[18px]";
const gradientClass =
  "bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to";

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
