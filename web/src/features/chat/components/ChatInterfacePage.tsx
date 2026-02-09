"use client";

import { useParams, useRouter } from "next/navigation";
import type { KeyboardEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChatEmptyState } from "@/features/chat/components/ChatEmptyState";
import { ChatInput } from "@/features/chat/components/ChatInput";
import { ChatMessages } from "@/features/chat/components/ChatMessages";
import { useChatSession } from "@/features/chat/hooks/useChatSession";
import { useChatStream } from "@/features/chat/hooks/useChatStream";
import {
  isReadyComposerAttachment,
  toMessageAttachment,
  useComposerAttachments,
} from "@/features/chat/hooks/useComposerAttachments";
import { brandVoices, quickActions } from "@/features/chat/model/constants";
import type { AssistantTurn } from "@/features/chat/model/types";
import { formatTime } from "@/features/chat/utils/chatViewUtils";

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
  const [brandVoiceIndex, setBrandVoiceIndex] = useState(0);

  const messageId = useRef(0);
  const chatWrapperRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
      answerText: "",
      reasoningText: "",
      notes: [],
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
      notes: [note],
    }),
    [createAssistantTurn],
  );

  const { activeChatId, timeline, setTimeline, messageInput, setMessageInput } =
    useChatSession({
      routeConversationId,
      textareaRef,
      clearPendingAttachments,
      createLoadErrorTurn,
    });

  const {
    isTyping,
    abortStream,
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

  // biome-ignore lint/correctness/useExhaustiveDependencies: route changes must cancel active streams.
  useEffect(() => {
    abortStream();
  }, [abortStream, routeConversationId]);

  useEffect(() => {
    if (!chatWrapperRef.current) {
      return;
    }
    if (timeline.length === 0 && !isTyping) {
      return;
    }
    chatWrapperRef.current.scrollTop = chatWrapperRef.current.scrollHeight;
  }, [timeline.length, isTyping]);

  const handleSend = async (overrideText?: string) => {
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
    });
  };

  const handleInputChange = (value: string) => {
    setMessageInput(value);
    if (!textareaRef.current) {
      return;
    }
    textareaRef.current.style.height = "auto";
    const nextHeight = Math.min(textareaRef.current.scrollHeight, 150);
    textareaRef.current.style.height = `${nextHeight}px`;
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSend();
    }
  };

  const toggleBrandVoice = () => {
    setBrandVoiceIndex((prev) => (prev + 1) % brandVoices.length);
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
    !hasUploadingAttachment;

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
          <ChatMessages timeline={timeline} isTyping={isTyping} />
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
        canSend={canSend}
        attachments={pendingAttachments}
        onPickFiles={handlePickFiles}
        onRemoveAttachment={handleRemoveAttachment}
        brandVoice={brandVoices[brandVoiceIndex]}
        onToggleBrandVoice={toggleBrandVoice}
      />
    </>
  );
}
