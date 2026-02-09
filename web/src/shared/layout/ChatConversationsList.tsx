import {
  MessageSquare,
  MoreHorizontal,
  PencilLine,
  Star,
  Trash2,
} from "lucide-react";
import type { ChatAction, ChatItem } from "@/features/chat/model/types";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";

const iconClass = "size-[18px]";
const iconSmallClass = "size-[14px]";
const menuItemClass = "cursor-pointer rounded-lg px-2.5 py-2";
type ChatStatus = ChatItem["status"];

const statusClasses: Record<ChatStatus, string> = {
  active:
    "bg-marketing-status-active/10 text-marketing-status-active border-marketing-status-active/20",
  draft:
    "bg-marketing-status-draft/10 text-marketing-status-draft border-marketing-status-draft/25",
};

const statusLabels: Record<ChatStatus, string> = {
  active: "Live",
  draft: "Draft",
};

type ChatConversationsListProps = {
  chatsOpen: boolean;
  chatItems: ChatItem[];
  activeChatId: string | null;
  onChatSelect: (chatId: string) => void;
  onChatAction: (action: ChatAction, chatId: string) => void;
  chatMenuOpenId: string | null;
  onChatMenuOpenChange: (chatId: string | null) => void;
};

export function ChatConversationsList({
  chatsOpen,
  chatItems,
  activeChatId,
  onChatSelect,
  onChatAction,
  chatMenuOpenId,
  onChatMenuOpenChange,
}: ChatConversationsListProps) {
  const hasChats = chatItems.length > 0;

  return (
    <div
      className={cn(
        "mt-3 flex flex-col gap-2 transition-[opacity,transform] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]",
        chatsOpen
          ? "translate-y-0 opacity-100"
          : "pointer-events-none -translate-y-2 opacity-0",
      )}
    >
      {!hasChats ? (
        <div className="rounded-lg border border-dashed border-marketing-border bg-marketing-surface px-3 py-4 text-xs text-marketing-text-muted">
          No chats yet. Start a conversation to see it here.
        </div>
      ) : (
        chatItems.map((chat) => {
          const isActive = activeChatId === chat.id;

          return (
            <div
              key={chat.id}
              className={cn(
                "relative flex items-start gap-2 rounded-lg border border-marketing-border bg-marketing-surface py-2.5 pr-2 pl-3 transition-all duration-200",
                !isActive && "hover:border-input hover:shadow-marketing-soft",
                isActive &&
                  "border-marketing-primary ring-1 ring-marketing-accent-ring/60",
              )}
            >
              <Button
                type="button"
                variant="ghost"
                className="h-auto min-w-0 flex-1 items-start justify-start px-0 py-0 text-left text-marketing-text-primary hover:bg-transparent hover:text-marketing-text-primary"
                onClick={() => onChatSelect(chat.id)}
              >
                <div className="flex min-w-0 flex-col gap-1">
                  <div className="flex min-w-0 items-center justify-between gap-2">
                    <span className="truncate">{chat.title}</span>
                    <span
                      className={cn(
                        "inline-flex shrink-0 items-center rounded-sm border px-1.5 py-0.5 text-[0.6rem] font-bold uppercase tracking-[0.06em]",
                        statusClasses[chat.status] ?? "border-marketing-border",
                      )}
                    >
                      {statusLabels[chat.status] ?? "Active"}
                    </span>
                  </div>
                  <div className="flex min-w-0 items-center gap-2 text-xs text-marketing-text-muted">
                    <span className="truncate">{chat.meta}</span>
                    {chat.starred && (
                      <Star
                        className={cn(
                          iconSmallClass,
                          "shrink-0 fill-current text-marketing-secondary",
                        )}
                        aria-hidden="true"
                      />
                    )}
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
                    className="h-8 w-8 rounded-md text-marketing-text-muted hover:bg-marketing-accent-medium hover:text-marketing-primary"
                    aria-label="Chat options"
                  >
                    <MoreHorizontal className={iconClass} aria-hidden="true" />
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
                      className={cn(iconClass, "text-marketing-text-primary")}
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
                      className={cn(iconClass, "text-marketing-text-primary")}
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
                      className={cn(iconClass, "text-marketing-text-primary")}
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
                      className={cn(iconClass, "text-marketing-danger")}
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
  );
}
