"use client";

import {
  ChevronLeft,
  ChevronRight,
  Settings as SettingsIcon,
} from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  tools as allTools,
  type ChatAction,
  type ChatItem,
  library,
  summarizeConversationMeta,
} from "@/features/chat";
import {
  type ConversationSummary,
  deleteAgentConversation,
  listAgentConversations,
  renameAgentConversation,
  starAgentConversation,
} from "@/shared/api/clients/agent.client";
import { env } from "@/shared/api/schemas/env";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { ChatHeader } from "./ChatHeader";
import { ChatSidebar } from "./ChatSidebar";

type AppShellProps = {
  children: ReactNode;
};

const CONVERSATIONS_PAGE_SIZE = 30;

export function AppShell({ children }: AppShellProps) {
  const sidebarId = "app-shell-sidebar";
  const router = useRouter();
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [chatsOpen, setChatsOpen] = useState(false);
  const [chatItems, setChatItems] = useState<ChatItem[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMoreConversations, setHasMoreConversations] = useState(false);
  const [isLoadingInitialConversations, setIsLoadingInitialConversations] =
    useState(false);
  const [isLoadingMoreConversations, setIsLoadingMoreConversations] =
    useState(false);
  const [chatMenuOpenId, setChatMenuOpenId] = useState<string | null>(null);
  const [activeTool, setActiveTool] = useState("assistant");
  const conversationsEpochRef = useRef(0);
  const visibleTools = useMemo(
    () =>
      allTools.filter(
        (item) => item.id !== "phoenix" || Boolean(env.NEXT_PUBLIC_PHOENIX_URL),
      ),
    [],
  );

  const isReferenceTablesRoute = pathname.startsWith("/reference-tables");
  const isSettingsRoute = pathname.startsWith("/settings");
  const activeChatId = useMemo(() => {
    const match = pathname.match(/^\/c\/([^/]+)$/);
    return match ? match[1] : null;
  }, [pathname]);

  const displayToolId = isReferenceTablesRoute
    ? "reference-tables"
    : activeTool;

  const { pageTitle, pageIcon: PageIcon } = useMemo(() => {
    if (isSettingsRoute) {
      return {
        pageTitle: "Model Settings",
        pageIcon: SettingsIcon,
      };
    }

    const allItems = [...visibleTools, ...library];
    const match =
      allItems.find((item) => item.id === displayToolId) ?? visibleTools[0];
    return {
      pageTitle: match.label,
      pageIcon: match.icon,
    };
  }, [displayToolId, isSettingsRoute, visibleTools]);

  const mapChatItem = useCallback(
    (conversation: ConversationSummary): ChatItem => ({
      id: conversation.id,
      title: conversation.title?.trim() || "Untitled conversation",
      meta: summarizeConversationMeta(conversation),
      status: "active",
      starred: conversation.starred,
    }),
    [],
  );

  const refreshConversations = useCallback(
    async (signal?: AbortSignal) => {
      const epoch = conversationsEpochRef.current + 1;
      conversationsEpochRef.current = epoch;
      setIsLoadingInitialConversations(true);
      setIsLoadingMoreConversations(false);
      setHasMoreConversations(false);
      setNextCursor(null);
      try {
        const page = await listAgentConversations({
          limit: CONVERSATIONS_PAGE_SIZE,
          signal,
        });
        if (conversationsEpochRef.current !== epoch) {
          return;
        }
        setChatItems(page.items.map(mapChatItem));
        setNextCursor(page.nextCursor ?? null);
        setHasMoreConversations(page.hasMore);
      } catch (error) {
        if (
          signal?.aborted ||
          (error instanceof DOMException && error.name === "AbortError")
        ) {
          return;
        }
        console.error("Failed to load conversations", error);
      } finally {
        if (conversationsEpochRef.current === epoch) {
          setIsLoadingInitialConversations(false);
        }
      }
    },
    [mapChatItem],
  );

  const loadMoreConversations = useCallback(async () => {
    if (
      isLoadingInitialConversations ||
      isLoadingMoreConversations ||
      !hasMoreConversations ||
      !nextCursor
    ) {
      return;
    }

    const epoch = conversationsEpochRef.current;
    setIsLoadingMoreConversations(true);
    try {
      const page = await listAgentConversations({
        limit: CONVERSATIONS_PAGE_SIZE,
        cursor: nextCursor,
      });
      if (conversationsEpochRef.current !== epoch) {
        return;
      }
      setChatItems((current) => {
        const existingIds = new Set(current.map((item) => item.id));
        const incoming = page.items
          .map(mapChatItem)
          .filter((item) => !existingIds.has(item.id));
        return [...current, ...incoming];
      });
      setNextCursor(page.nextCursor ?? null);
      setHasMoreConversations(page.hasMore);
    } catch (error) {
      console.error("Failed to load more conversations", error);
    } finally {
      if (conversationsEpochRef.current === epoch) {
        setIsLoadingMoreConversations(false);
      }
    }
  }, [
    hasMoreConversations,
    isLoadingInitialConversations,
    isLoadingMoreConversations,
    mapChatItem,
    nextCursor,
  ]);

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth <= 768) {
        setSidebarOpen(false);
      }
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    if (isReferenceTablesRoute) {
      setActiveTool("reference-tables");
      return;
    }
    setActiveTool((current) =>
      current === "reference-tables" ? "assistant" : current,
    );
  }, [isReferenceTablesRoute]);

  useEffect(() => {
    const controller = new AbortController();
    void refreshConversations(controller.signal);
    return () => controller.abort();
  }, [refreshConversations]);

  useEffect(() => {
    const handleRefresh = () => {
      void refreshConversations();
    };

    window.addEventListener("agent-conversations:refresh", handleRefresh);
    return () =>
      window.removeEventListener("agent-conversations:refresh", handleRefresh);
  }, [refreshConversations]);

  const closeSidebarOnMobile = () => {
    if (window.innerWidth <= 768) {
      setSidebarOpen(false);
    }
  };

  const handleToolClick = (toolId: string) => {
    if (toolId === "phoenix") {
      if (env.NEXT_PUBLIC_PHOENIX_URL) {
        window.open(
          env.NEXT_PUBLIC_PHOENIX_URL,
          "_blank",
          "noopener,noreferrer",
        );
      }
      setChatMenuOpenId(null);
      closeSidebarOnMobile();
      return;
    }

    setActiveTool(toolId);
    setChatMenuOpenId(null);
    if (toolId === "reference-tables") {
      router.push("/reference-tables");
    } else if (isReferenceTablesRoute || isSettingsRoute) {
      router.push("/");
    }
    closeSidebarOnMobile();
  };

  const handleOpenSettings = () => {
    setChatMenuOpenId(null);
    router.push("/settings/model");
    closeSidebarOnMobile();
  };

  const handleChatSelect = (chatId: string) => {
    setChatMenuOpenId(null);
    router.push(`/c/${chatId}`);
    closeSidebarOnMobile();
  };

  const handleNewChat = () => {
    setActiveTool("assistant");
    setChatMenuOpenId(null);
    router.push("/");
    window.dispatchEvent(new Event("agent-chat:reset"));
    closeSidebarOnMobile();
  };

  const handleChatAction = (action: ChatAction, chatId: string) => {
    if (action === "use") {
      handleChatSelect(chatId);
      return;
    }

    if (action === "rename") {
      const current = chatItems.find((item) => item.id === chatId);
      if (!current) return;
      const nextTitle = window.prompt("Rename chat", current.title);
      if (!nextTitle || !nextTitle.trim()) return;
      const normalizedTitle = nextTitle.trim();
      void (async () => {
        try {
          await renameAgentConversation(chatId, normalizedTitle);
          await refreshConversations();
        } catch (error) {
          console.error("Failed to rename conversation", error);
        } finally {
          setChatMenuOpenId(null);
        }
      })();
      return;
    }

    if (action === "delete") {
      void (async () => {
        try {
          await deleteAgentConversation(chatId);
          if (activeChatId === chatId) {
            router.push("/");
            window.dispatchEvent(new Event("agent-chat:reset"));
          }
          await refreshConversations();
        } catch (error) {
          console.error("Failed to delete conversation", error);
        } finally {
          setChatMenuOpenId(null);
        }
      })();
      return;
    }

    if (action === "star") {
      const current = chatItems.find((item) => item.id === chatId);
      if (!current) return;
      const nextStarred = !current.starred;
      void (async () => {
        try {
          await starAgentConversation(chatId, nextStarred);
          await refreshConversations();
        } catch (error) {
          console.error("Failed to update star status", error);
        } finally {
          setChatMenuOpenId(null);
        }
      })();
    }
  };

  return (
    <div className="relative flex h-screen overflow-hidden bg-marketing-bg font-sans text-marketing-text-primary">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,var(--color-marketing-accent-soft),transparent_42%)]" />
      <button
        type="button"
        aria-label="Close sidebar"
        className={cn(
          "fixed inset-0 z-[99] bg-marketing-overlay backdrop-blur-[4px] md:hidden",
          sidebarOpen ? "block" : "hidden",
        )}
        onClick={() => setSidebarOpen(false)}
      />

      <ChatSidebar
        isOpen={sidebarOpen}
        chatsOpen={chatsOpen}
        onToggleChats={() => setChatsOpen((prev) => !prev)}
        onNewChat={handleNewChat}
        chatItems={chatItems}
        activeChatId={activeChatId}
        onChatSelect={handleChatSelect}
        onChatAction={handleChatAction}
        chatMenuOpenId={chatMenuOpenId}
        onChatMenuOpenChange={setChatMenuOpenId}
        hasMoreConversations={hasMoreConversations}
        isLoadingInitialConversations={isLoadingInitialConversations}
        isLoadingMoreConversations={isLoadingMoreConversations}
        onLoadMoreConversations={loadMoreConversations}
        tools={visibleTools}
        library={library}
        activeTool={displayToolId}
        onToolSelect={handleToolClick}
        onOpenSettings={handleOpenSettings}
      />
      <Button
        type="button"
        variant="outline"
        size="icon-sm"
        aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
        aria-expanded={sidebarOpen}
        aria-controls={sidebarId}
        className={cn(
          "fixed top-1/2 z-[110] -translate-y-1/2 border-marketing-border bg-marketing-surface text-marketing-text-secondary shadow-marketing-soft transition-[left,transform,background-color,color] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] hover:bg-marketing-accent-medium hover:text-marketing-text-primary",
          sidebarOpen ? "left-[280px] -translate-x-1/2" : "left-3",
        )}
        onClick={() => setSidebarOpen((prev) => !prev)}
      >
        {sidebarOpen ? (
          <ChevronLeft className="size-4" aria-hidden="true" />
        ) : (
          <ChevronRight className="size-4" aria-hidden="true" />
        )}
      </Button>

      <main className="relative z-[1] flex flex-1 flex-col overflow-hidden bg-marketing-bg">
        <ChatHeader pageTitle={pageTitle} PageIcon={PageIcon} />
        {children}
      </main>
    </div>
  );
}
