"use client";

import { useParams, useRouter } from "next/navigation";
import type { KeyboardEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChatEmptyState } from "@/components/chat-interface/ChatEmptyState";
import { ChatInput } from "@/components/chat-interface/ChatInput";
import { ChatMessages } from "@/components/chat-interface/ChatMessages";
import {
  brandVoices,
  quickActions,
} from "@/components/chat-interface/constants";
import type { Message } from "@/components/chat-interface/types";
import {
  isReadyComposerAttachment,
  toMessageAttachment,
  useComposerAttachments,
} from "@/components/chat-interface/useComposerAttachments";
import {
  getAgentConversation,
  streamAgent,
} from "@/lib/api/clients/agent.client";
import {
  formatMetaBlock,
  formatTime,
  formatToolCall,
  formatToolDelta,
  formatToolResult,
  mapConversationKind,
} from "@/view/chatViewUtils";

export function ChatInterfaceView() {
  const router = useRouter();
  const params = useParams<{ conversationId?: string }>();
  const routeConversationId =
    typeof params?.conversationId === "string" ? params.conversationId : null;

  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [messageInput, setMessageInput] = useState("");
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
  const streamAbortRef = useRef<AbortController | null>(null);
  const streamStateRef = useRef({
    textId: null as number | null,
    reasoningId: null as number | null,
    toolDelta: new Map<
      number,
      { id: number; name?: string; args?: string; callId?: string }
    >(),
  });
  const hasStreamedRef = useRef(false);

  useEffect(() => {
    if (!chatWrapperRef.current) return;
    if (messages.length === 0 && !isTyping) return;
    chatWrapperRef.current.scrollTop = chatWrapperRef.current.scrollHeight;
  }, [messages.length, isTyping]);

  useEffect(() => {
    return () => {
      streamAbortRef.current?.abort();
    };
  }, []);

  const loadConversation = useCallback(async (conversationId: string) => {
    const conversation = await getAgentConversation(conversationId);
    setActiveChatId(conversation.id);
    setMessages(
      conversation.messages
        .sort(
          (a, b) =>
            new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
        )
        .map((message) => ({
          id: messageId.current++,
          sender: message.role === "user" ? "user" : "bot",
          text: message.content,
          time: formatTime(new Date(message.createdAt)),
          kind:
            message.role === "assistant"
              ? mapConversationKind(message.messageKind)
              : undefined,
          attachments: message.attachments
            .sort((a, b) => a.position - b.position)
            .map((attachment) => ({
              id: attachment.id,
              filename: attachment.filename,
              contentType: attachment.contentType,
              mediaType: attachment.mediaType,
              sizeBytes: attachment.sizeBytes,
              previewText: attachment.previewText,
              extractionNote: attachment.extractionNote,
              localPreviewUrl:
                attachment.mediaType === "image"
                  ? attachment.downloadUrl
                  : undefined,
            })),
        })),
    );
  }, []);

  useEffect(() => {
    let cancelled = false;
    streamAbortRef.current?.abort();
    setIsTyping(false);

    if (!routeConversationId) {
      setActiveChatId(null);
      setMessages([]);
      setMessageInput("");
      clearPendingAttachments();
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
      return () => {
        cancelled = true;
      };
    }
    setActiveChatId(routeConversationId);

    (async () => {
      try {
        await loadConversation(routeConversationId);
      } catch (error) {
        if (cancelled) {
          return;
        }
        setActiveChatId(null);
        setMessages([
          {
            id: messageId.current++,
            sender: "bot",
            text:
              error instanceof Error
                ? `Failed to load conversation: ${error.message}`
                : "Failed to load conversation.",
            time: formatTime(new Date()),
            kind: "meta",
          },
        ]);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [routeConversationId, loadConversation, clearPendingAttachments]);

  const addMessage = (
    text: string,
    sender: Message["sender"],
    kind?: Message["kind"],
    attachments?: Message["attachments"],
  ) => {
    const nextMessage: Message = {
      id: messageId.current++,
      sender,
      text,
      time: formatTime(new Date()),
      kind,
      attachments,
    };
    setMessages((prev) => [...prev, nextMessage]);
  };

  const updateMessageText = (id: number, nextText: string) => {
    setMessages((prev) =>
      prev.map((message) =>
        message.id === id ? { ...message, text: nextText } : message,
      ),
    );
  };

  const appendMessageText = (id: number, nextChunk: string) => {
    setMessages((prev) =>
      prev.map((message) =>
        message.id === id
          ? { ...message, text: `${message.text}${nextChunk}` }
          : message,
      ),
    );
  };

  const resetStreamState = useCallback(() => {
    streamStateRef.current = {
      textId: null,
      reasoningId: null,
      toolDelta: new Map(),
    };
    hasStreamedRef.current = false;
  }, []);

  useEffect(() => {
    const handleReset = () => {
      streamAbortRef.current?.abort();
      resetStreamState();
      setIsTyping(false);
      setActiveChatId(null);
      setMessages([]);
      setMessageInput("");
      clearPendingAttachments();
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    };

    window.addEventListener("agent-chat:reset", handleReset);
    return () => {
      window.removeEventListener("agent-chat:reset", handleReset);
    };
  }, [clearPendingAttachments, resetStreamState]);

  const ensureStreamMessage = (
    key: "textId" | "reasoningId",
    initialText: string,
  ) => {
    const currentId = streamStateRef.current[key];
    if (currentId !== null) {
      return currentId;
    }
    const id = messageId.current++;
    setMessages((prev) => [
      ...prev,
      {
        id,
        sender: "bot",
        text: initialText,
        time: formatTime(new Date()),
        kind: key === "reasoningId" ? "reasoning" : "assistant",
      },
    ]);
    streamStateRef.current[key] = id;
    return id;
  };

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
      addMessage(
        "Wait for file uploads to finish before sending.",
        "bot",
        "meta",
      );
      return;
    }

    if (!text && readyAttachments.length === 0) return;

    streamAbortRef.current?.abort();
    resetStreamState();

    const userAttachments = readyAttachments.map(toMessageAttachment);

    addMessage(text || "Sent attachments.", "user", undefined, userAttachments);
    setMessageInput("");
    setPendingAttachments((prev) =>
      prev.filter(
        (item) => !readyAttachments.some((ready) => ready.id === item.id),
      ),
    );

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    setIsTyping(true);

    const abortController = new AbortController();
    streamAbortRef.current = abortController;

    try {
      await streamAgent({
        message: text,
        conversationId: activeChatId,
        attachmentIds: readyAttachments.map((item) => item.fileId),
        signal: abortController.signal,
        onEvent: (event) => {
          if (!hasStreamedRef.current) {
            setIsTyping(false);
            hasStreamedRef.current = true;
          }
          if (event.type === "text_delta") {
            const id = ensureStreamMessage("textId", "");
            appendMessageText(id, event.content);
            return;
          }
          if (event.type === "reasoning_delta") {
            const id = ensureStreamMessage("reasoningId", "");
            appendMessageText(id, event.content);
            return;
          }
          if (event.type === "tool_call_delta") {
            const index = event.index ?? 0;
            let entry = streamStateRef.current.toolDelta.get(index);
            if (!entry) {
              const id = messageId.current++;
              entry = { id, name: event.name ?? "", args: "" };
              streamStateRef.current.toolDelta.set(index, entry);
              setMessages((prev) => [
                ...prev,
                {
                  id,
                  sender: "bot",
                  text: "",
                  time: formatTime(new Date()),
                  kind: "tool_call",
                },
              ]);
            }
            if (event.name) {
              entry.name = event.name;
            }
            if (event.id) {
              entry.callId = event.id;
            }
            if (event.args) {
              entry.args = `${entry.args ?? ""}${event.args}`;
            }
            updateMessageText(entry.id, formatToolDelta(entry));
            return;
          }
          if (event.type === "tool_call") {
            let matched = false;
            if (event.id) {
              for (const entry of streamStateRef.current.toolDelta.values()) {
                if (entry.callId === event.id) {
                  updateMessageText(entry.id, formatToolCall(event));
                  matched = true;
                  break;
                }
              }
            }
            if (!matched) {
              addMessage(formatToolCall(event), "bot", "tool_call");
            }
            return;
          }
          if (event.type === "tool_result") {
            addMessage(formatToolResult(event), "bot", "tool_result");
            return;
          }
          if (event.type === "final") {
            const id = ensureStreamMessage("textId", "");
            updateMessageText(id, event.output_text);
            if (
              event.conversation_id &&
              event.conversation_id !== activeChatId
            ) {
              router.replace(`/c/${event.conversation_id}`);
            }
            const usageText = formatMetaBlock("usage", event.usage);
            if (usageText) {
              addMessage(usageText, "bot", "meta");
            }
            const metadataText = formatMetaBlock(
              "response_metadata",
              event.response_metadata,
            );
            if (metadataText) {
              addMessage(metadataText, "bot", "meta");
            }
            window.dispatchEvent(new Event("agent-conversations:refresh"));
            setIsTyping(false);
            return;
          }
        },
      });
    } catch (error) {
      if (abortController.signal.aborted) {
        return;
      }
      setIsTyping(false);
      addMessage(
        error instanceof Error
          ? `Something went wrong: ${error.message}`
          : "Something went wrong while streaming the response.",
        "bot",
        "meta",
      );
    } finally {
      if (streamAbortRef.current === abortController) {
        streamAbortRef.current = null;
      }
    }
  };

  const handleQuickAction = (prompt: string) => {
    handleSend(prompt);
  };

  const handleInputChange = (value: string) => {
    setMessageInput(value);
    if (!textareaRef.current) return;
    textareaRef.current.style.height = "auto";
    const nextHeight = Math.min(textareaRef.current.scrollHeight, 150);
    textareaRef.current.style.height = `${nextHeight}px`;
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const toggleBrandVoice = () => {
    setBrandVoiceIndex((prev) => (prev + 1) % brandVoices.length);
  };

  const hasMessages = messages.length > 0;
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
        className="flex flex-1 flex-col overflow-y-auto p-4 md:p-8"
        ref={chatWrapperRef}
      >
        {!hasMessages ? (
          <ChatEmptyState actions={quickActions} onAction={handleQuickAction} />
        ) : (
          <ChatMessages messages={messages} isTyping={isTyping} />
        )}
      </div>

      <ChatInput
        textareaRef={textareaRef}
        value={messageInput}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onSend={handleSend}
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
