import type { RefObject } from "react";
import { useCallback, useEffect, useState } from "react";
import type {
  AssistantTurn,
  ChatTimelineItem,
} from "@/features/chat/model/types";
import { groupConversationMessages } from "@/features/chat/utils/chatViewUtils";
import { getAgentConversation } from "@/shared/api/clients/agent.client";

type UseChatSessionParams = {
  routeConversationId: string | null;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  clearPendingAttachments: () => void;
  createLoadErrorTurn: (note: string) => AssistantTurn;
};

export function useChatSession({
  routeConversationId,
  textareaRef,
  clearPendingAttachments,
  createLoadErrorTurn,
}: UseChatSessionParams) {
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<ChatTimelineItem[]>([]);
  const [messageInput, setMessageInput] = useState("");

  const resetComposer = useCallback(() => {
    setMessageInput("");
    clearPendingAttachments();
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [clearPendingAttachments, textareaRef]);

  const loadConversation = useCallback(async (conversationId: string) => {
    const conversation = await getAgentConversation(conversationId);
    setActiveChatId(conversation.id);
    setTimeline(groupConversationMessages(conversation.messages));
  }, []);

  useEffect(() => {
    let cancelled = false;

    if (!routeConversationId) {
      setActiveChatId(null);
      setTimeline([]);
      resetComposer();
      return () => {
        cancelled = true;
      };
    }

    setActiveChatId(routeConversationId);

    void (async () => {
      try {
        await loadConversation(routeConversationId);
      } catch (error) {
        if (cancelled) {
          return;
        }

        setActiveChatId(null);
        setTimeline([
          createLoadErrorTurn(
            error instanceof Error
              ? `Failed to load conversation: ${error.message}`
              : "Failed to load conversation.",
          ),
        ]);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    createLoadErrorTurn,
    loadConversation,
    resetComposer,
    routeConversationId,
  ]);

  useEffect(() => {
    const handleReset = () => {
      setActiveChatId(null);
      setTimeline([]);
      resetComposer();
    };

    window.addEventListener("agent-chat:reset", handleReset);
    return () => {
      window.removeEventListener("agent-chat:reset", handleReset);
    };
  }, [resetComposer]);

  return {
    activeChatId,
    timeline,
    setTimeline,
    messageInput,
    setMessageInput,
  };
}
