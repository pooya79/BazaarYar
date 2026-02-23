"use client";

import { useParams, useRouter } from "next/navigation";
import type { KeyboardEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChatEmptyState } from "@/features/chat/components/ChatEmptyState";
import {
  ChatInput,
  type PromptSuggestion,
} from "@/features/chat/components/ChatInput";
import { ChatMessages } from "@/features/chat/components/ChatMessages";
import { ToolSettingsModal } from "@/features/chat/components/ToolSettingsModal";
import { useChatSession } from "@/features/chat/hooks/useChatSession";
import { useChatStream } from "@/features/chat/hooks/useChatStream";
import {
  isReadyComposerAttachment,
  toMessageAttachment,
  useComposerAttachments,
} from "@/features/chat/hooks/useComposerAttachments";
import { useToolSettings } from "@/features/chat/hooks/useToolSettings";
import { quickActions } from "@/features/chat/model/constants";
import type { AssistantTurn } from "@/features/chat/model/types";
import { formatTime } from "@/features/chat/utils/chatViewUtils";
import { replaceTrailingPromptCommand } from "@/features/prompts/model/promptStore";
import { listPrompts } from "@/shared/api/clients/prompts.client";
import { useModelCards } from "@/shared/layout/ModelCardsContext";

export function ChatInterfacePage() {
  const router = useRouter();
  const params = useParams<{ conversationId?: string }>();
  const routeConversationId =
    typeof params?.conversationId === "string" ? params.conversationId : null;

  const {
    pendingAttachments,
    setPendingAttachments,
    handlePickFiles,
    handleRemoveAttachment,
    clearPendingAttachments,
  } = useComposerAttachments();
  const [toolModalOpen, setToolModalOpen] = useState(false);

  const messageId = useRef(0);
  const chatWrapperRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [debouncedPromptQuery, setDebouncedPromptQuery] = useState<
    string | null
  >(null);
  const [promptSuggestions, setPromptSuggestions] = useState<
    PromptSuggestion[]
  >([]);
  const [isPromptSuggestionsDismissed, setIsPromptSuggestionsDismissed] =
    useState(false);
  const [activePromptSuggestionIndex, setActivePromptSuggestionIndex] =
    useState(0);

  const createLocalId = useCallback(() => {
    const id = `local-${messageId.current}`;
    messageId.current += 1;
    return id;
  }, []);

  const createAssistantTurn = useCallback((): AssistantTurn => {
    return {
      id: createLocalId(),
      sender: "assistant",
      time: formatTime(new Date()),
      blocks: [],
      toolCalls: [],
      attachments: [],
      usage: null,
      responseMetadata: null,
      reasoningTokens: null,
    };
  }, [createLocalId]);

  const createLoadErrorTurn = useCallback(
    (note: string): AssistantTurn => ({
      ...createAssistantTurn(),
      blocks: [
        {
          id: `${createLocalId()}:note:load-error`,
          type: "note",
          content: note,
        },
      ],
    }),
    [createAssistantTurn, createLocalId],
  );

  const { activeChatId, timeline, setTimeline, messageInput, setMessageInput } =
    useChatSession({
      routeConversationId,
      textareaRef,
      clearPendingAttachments,
      createLoadErrorTurn,
    });

  const {
    isStreaming,
    showTypingIndicator,
    abortStream,
    stopStream,
    addAssistantNote,
    addUserMessage,
    startStream,
  } = useChatStream({
    activeChatId,
    setTimeline,
    createLocalId,
    createAssistantTurn,
    onConversationRedirect: (conversationId) => {
      router.replace(`/c/${conversationId}`);
    },
  });

  const {
    groups: toolGroups,
    isLoading: isToolSettingsLoading,
    isSaving: isToolSettingsSaving,
    loadError: toolSettingsLoadError,
    saveError: toolSettingsSaveError,
    hasUnsavedChanges: hasUnsavedToolChanges,
    toggleTool,
    toggleGroup,
    reload: reloadToolSettings,
    save: saveToolSettings,
    discardChanges: discardToolChanges,
  } = useToolSettings();
  const { selectedModelId } = useModelCards();

  // biome-ignore lint/correctness/useExhaustiveDependencies: route changes must cancel active streams.
  useEffect(() => {
    abortStream();
  }, [abortStream, routeConversationId]);

  useEffect(() => {
    if (!chatWrapperRef.current) {
      return;
    }
    if (timeline.length === 0 && !showTypingIndicator) {
      return;
    }
    chatWrapperRef.current.scrollTop = chatWrapperRef.current.scrollHeight;
  }, [timeline.length, showTypingIndicator]);

  const trailingPromptMatch = messageInput.match(/\\([a-zA-Z0-9_-]*)$/);
  const promptSearchQuery = trailingPromptMatch
    ? trailingPromptMatch[1].toLowerCase()
    : null;

  useEffect(() => {
    if (promptSearchQuery === null) {
      setDebouncedPromptQuery(null);
      return;
    }
    const timeoutId = window.setTimeout(() => {
      setDebouncedPromptQuery(promptSearchQuery);
    }, 140);
    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [promptSearchQuery]);

  useEffect(() => {
    if (debouncedPromptQuery === null || isPromptSuggestionsDismissed) {
      setPromptSuggestions([]);
      return;
    }

    const controller = new AbortController();
    void (async () => {
      try {
        const items = await listPrompts({
          q: debouncedPromptQuery,
          limit: 3,
          offset: 0,
          signal: controller.signal,
        });
        setPromptSuggestions(
          items.map((item) => ({
            id: item.id,
            name: item.name,
            description: item.description,
            prompt: item.prompt,
          })),
        );
      } catch (error) {
        if (
          controller.signal.aborted ||
          (error instanceof DOMException && error.name === "AbortError")
        ) {
          return;
        }
        console.error("Failed to fetch prompt suggestions", error);
        setPromptSuggestions([]);
      }
    })();

    return () => controller.abort();
  }, [debouncedPromptQuery, isPromptSuggestionsDismissed]);

  useEffect(() => {
    setActivePromptSuggestionIndex((current) => {
      if (promptSuggestions.length === 0) {
        return 0;
      }
      return Math.min(current, promptSuggestions.length - 1);
    });
  }, [promptSuggestions]);

  const resizeComposer = useCallback(() => {
    if (!textareaRef.current) {
      return;
    }
    textareaRef.current.style.height = "auto";
    const nextHeight = Math.min(textareaRef.current.scrollHeight, 150);
    textareaRef.current.style.height = `${nextHeight}px`;
  }, []);

  const applyPromptSuggestion = useCallback(
    (index: number) => {
      const selectedPrompt = promptSuggestions[index];
      if (!selectedPrompt) {
        return false;
      }
      setMessageInput((current) =>
        replaceTrailingPromptCommand(current, selectedPrompt.prompt),
      );
      setIsPromptSuggestionsDismissed(true);
      window.requestAnimationFrame(() => {
        resizeComposer();
        textareaRef.current?.focus();
      });
      return true;
    },
    [promptSuggestions, resizeComposer, setMessageInput],
  );

  const handleSend = async (overrideText?: string) => {
    if (isStreaming) {
      return;
    }

    const baseText =
      typeof overrideText === "string" ? overrideText : messageInput;
    const text = baseText.trim();

    const uploadingCount = pendingAttachments.filter(
      (item) => item.status === "uploading",
    ).length;
    const readyAttachments = pendingAttachments.filter(
      isReadyComposerAttachment,
    );

    if (uploadingCount > 0) {
      addAssistantNote("Wait for file uploads to finish before sending.");
      return;
    }

    if (!text && readyAttachments.length === 0) {
      return;
    }

    const userAttachments = readyAttachments.map(toMessageAttachment);

    addUserMessage(text || "Sent attachments.", userAttachments);
    setMessageInput("");
    setPendingAttachments((prev) =>
      prev.filter(
        (item) => !readyAttachments.some((ready) => ready.id === item.id),
      ),
    );

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    await startStream({
      message: text,
      conversationId: activeChatId,
      attachmentIds: readyAttachments.map((item) => item.fileId),
      modelId: selectedModelId,
    });
  };

  const handleInputChange = (value: string) => {
    setIsPromptSuggestionsDismissed(false);
    setMessageInput(value);
    resizeComposer();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (promptSuggestions.length > 0) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setActivePromptSuggestionIndex((current) =>
          current + 1 >= promptSuggestions.length ? 0 : current + 1,
        );
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setActivePromptSuggestionIndex((current) =>
          current - 1 < 0 ? promptSuggestions.length - 1 : current - 1,
        );
        return;
      }
      if ((event.key === "Enter" && !event.shiftKey) || event.key === "Tab") {
        event.preventDefault();
        applyPromptSuggestion(activePromptSuggestionIndex);
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        setIsPromptSuggestionsDismissed(true);
        return;
      }
    }

    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (isStreaming) {
        stopStream();
        return;
      }
      void handleSend();
    }
  };

  const hasMessages = timeline.length > 0;
  const hasReadyAttachment = pendingAttachments.some(
    (item) => item.status === "ready",
  );
  const hasUploadingAttachment = pendingAttachments.some(
    (item) => item.status === "uploading",
  );
  const canSend =
    (messageInput.trim().length > 0 || hasReadyAttachment) &&
    !hasUploadingAttachment &&
    !isStreaming;

  return (
    <>
      <div
        className="flex flex-1 flex-col overflow-y-auto px-6 py-8 md:px-10 md:py-10"
        ref={chatWrapperRef}
      >
        {!hasMessages ? (
          <ChatEmptyState
            actions={quickActions}
            onAction={(prompt) => {
              void handleSend(prompt);
            }}
          />
        ) : (
          <ChatMessages
            timeline={timeline}
            showTypingIndicator={showTypingIndicator}
          />
        )}
      </div>

      <ChatInput
        textareaRef={textareaRef}
        value={messageInput}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onSend={() => {
          void handleSend();
        }}
        isStreaming={isStreaming}
        onStop={stopStream}
        canSend={canSend}
        attachments={pendingAttachments}
        onPickFiles={handlePickFiles}
        onRemoveAttachment={handleRemoveAttachment}
        onOpenToolSettings={() => setToolModalOpen(true)}
        toolSettingsBusy={isToolSettingsLoading}
        promptSuggestions={promptSuggestions}
        activePromptSuggestionIndex={activePromptSuggestionIndex}
        onPromptSuggestionHover={setActivePromptSuggestionIndex}
        onPromptSuggestionSelect={applyPromptSuggestion}
      />
      <ToolSettingsModal
        open={toolModalOpen}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) {
            discardToolChanges();
          }
          setToolModalOpen(nextOpen);
        }}
        groups={toolGroups}
        isLoading={isToolSettingsLoading}
        isSaving={isToolSettingsSaving}
        hasUnsavedChanges={hasUnsavedToolChanges}
        loadError={toolSettingsLoadError}
        saveError={toolSettingsSaveError}
        onToggleGroup={toggleGroup}
        onToggleTool={toggleTool}
        onReload={() => {
          void reloadToolSettings();
        }}
        onSave={saveToolSettings}
        onDiscard={discardToolChanges}
      />
    </>
  );
}
