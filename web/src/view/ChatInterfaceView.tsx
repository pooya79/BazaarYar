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
import type {
  AssistantTurn,
  ChatTimelineItem,
  MessageAttachment,
} from "@/components/chat-interface/types";
import {
  isReadyComposerAttachment,
  toMessageAttachment,
  useComposerAttachments,
} from "@/components/chat-interface/useComposerAttachments";
import {
  getAgentConversation,
  streamAgent,
} from "@/lib/api/clients/agent.client";
import { buildUrl } from "@/lib/api/http";
import {
  extractReasoningTokens,
  formatSandboxStatus,
  formatTime,
  groupConversationMessages,
} from "@/view/chatViewUtils";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function mergeAttachments(
  existing: MessageAttachment[],
  incoming: MessageAttachment[],
) {
  if (incoming.length === 0) {
    return existing;
  }
  const byId = new Map(
    existing.map((attachment) => [attachment.id, attachment]),
  );
  for (const attachment of incoming) {
    byId.set(attachment.id, attachment);
  }
  return Array.from(byId.values());
}

export function ChatInterfaceView() {
  const router = useRouter();
  const params = useParams<{ conversationId?: string }>();
  const routeConversationId =
    typeof params?.conversationId === "string" ? params.conversationId : null;

  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<ChatTimelineItem[]>([]);
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
    assistantTurnId: null as string | null,
    toolKeysByIndex: new Map<number, string>(),
    toolKeysByCallId: new Map<string, string>(),
    sandboxNoteIndexByRunId: new Map<string, number>(),
    nextToolSeq: 0,
  });
  const hasStreamedRef = useRef(false);

  const createLocalId = useCallback(() => {
    const id = `local-${messageId.current}`;
    messageId.current += 1;
    return id;
  }, []);

  useEffect(() => {
    if (!chatWrapperRef.current) return;
    if (timeline.length === 0 && !isTyping) return;
    chatWrapperRef.current.scrollTop = chatWrapperRef.current.scrollHeight;
  }, [timeline.length, isTyping]);

  useEffect(() => {
    return () => {
      streamAbortRef.current?.abort();
    };
  }, []);

  const resetStreamState = useCallback(() => {
    streamStateRef.current = {
      assistantTurnId: null,
      toolKeysByIndex: new Map(),
      toolKeysByCallId: new Map(),
      sandboxNoteIndexByRunId: new Map(),
      nextToolSeq: 0,
    };
    hasStreamedRef.current = false;
  }, []);

  const loadConversation = useCallback(async (conversationId: string) => {
    const conversation = await getAgentConversation(conversationId);
    setActiveChatId(conversation.id);
    setTimeline(groupConversationMessages(conversation.messages));
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

  const ensureActiveAssistantTurn = useCallback(() => {
    const activeTurnId = streamStateRef.current.assistantTurnId;
    if (activeTurnId) {
      return activeTurnId;
    }
    const turn = createAssistantTurn();
    setTimeline((prev) => [...prev, turn]);
    streamStateRef.current.assistantTurnId = turn.id;
    return turn.id;
  }, [createAssistantTurn]);

  const updateAssistantTurn = useCallback(
    (turnId: string, updater: (turn: AssistantTurn) => AssistantTurn) => {
      setTimeline((prev) =>
        prev.map((item) => {
          if (item.sender !== "assistant" || item.id !== turnId) {
            return item;
          }
          return updater(item);
        }),
      );
    },
    [],
  );

  const appendAssistantAnswer = useCallback(
    (chunk: string) => {
      const turnId = ensureActiveAssistantTurn();
      updateAssistantTurn(turnId, (turn) => ({
        ...turn,
        answerText: `${turn.answerText}${chunk}`,
      }));
    },
    [ensureActiveAssistantTurn, updateAssistantTurn],
  );

  const appendAssistantReasoning = useCallback(
    (chunk: string) => {
      const turnId = ensureActiveAssistantTurn();
      updateAssistantTurn(turnId, (turn) => ({
        ...turn,
        reasoningText: `${turn.reasoningText}${chunk}`,
      }));
    },
    [ensureActiveAssistantTurn, updateAssistantTurn],
  );

  const addAssistantNote = useCallback(
    (note: string) => {
      setTimeline((prev) => {
        const lastItem = prev.at(-1);
        if (lastItem?.sender === "assistant") {
          return prev.map((item) => {
            if (item.id !== lastItem.id || item.sender !== "assistant") {
              return item;
            }
            return {
              ...item,
              notes: [...item.notes, note],
            };
          });
        }
        const turn = createAssistantTurn();
        return [...prev, { ...turn, notes: [note] }];
      });
    },
    [createAssistantTurn],
  );

  const addUserMessage = useCallback(
    (text: string, attachments?: MessageAttachment[]) => {
      setTimeline((prev) => [
        ...prev,
        {
          id: createLocalId(),
          sender: "user",
          text,
          time: formatTime(new Date()),
          attachments,
        },
      ]);
    },
    [createLocalId],
  );

  useEffect(() => {
    let cancelled = false;
    streamAbortRef.current?.abort();
    setIsTyping(false);

    if (!routeConversationId) {
      setActiveChatId(null);
      setTimeline([]);
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
        setTimeline([
          {
            ...createAssistantTurn(),
            notes: [
              error instanceof Error
                ? `Failed to load conversation: ${error.message}`
                : "Failed to load conversation.",
            ],
          },
        ]);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    routeConversationId,
    loadConversation,
    clearPendingAttachments,
    createAssistantTurn,
  ]);

  useEffect(() => {
    const handleReset = () => {
      streamAbortRef.current?.abort();
      resetStreamState();
      setIsTyping(false);
      setActiveChatId(null);
      setTimeline([]);
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

    if (!text && readyAttachments.length === 0) return;

    streamAbortRef.current?.abort();
    resetStreamState();

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
            appendAssistantAnswer(event.content);
            return;
          }

          if (event.type === "reasoning_delta") {
            appendAssistantReasoning(event.content);
            return;
          }

          if (event.type === "tool_call_delta") {
            const turnId = ensureActiveAssistantTurn();
            const streamIndex =
              typeof event.index === "number" ? event.index : null;
            const knownKeyByCallId = event.id?.trim()
              ? streamStateRef.current.toolKeysByCallId.get(event.id)
              : undefined;
            const knownKeyByIndex =
              streamIndex !== null
                ? streamStateRef.current.toolKeysByIndex.get(streamIndex)
                : undefined;
            const knownKey = knownKeyByCallId || knownKeyByIndex;

            updateAssistantTurn(turnId, (turn) => {
              const toolCalls = turn.toolCalls.slice();
              let targetIndex = knownKey
                ? toolCalls.findIndex((item) => item.key === knownKey)
                : -1;

              if (targetIndex < 0 && event.id) {
                targetIndex = toolCalls.findIndex(
                  (item) => item.callId === event.id,
                );
              }

              if (targetIndex < 0) {
                const key = `${turn.id}:tool:${streamStateRef.current.nextToolSeq++}`;
                if (streamIndex !== null) {
                  streamStateRef.current.toolKeysByIndex.set(streamIndex, key);
                }
                if (event.id) {
                  streamStateRef.current.toolKeysByCallId.set(event.id, key);
                }
                return {
                  ...turn,
                  toolCalls: [
                    ...toolCalls,
                    {
                      key,
                      name: event.name ?? "unknown",
                      callId: event.id,
                      streamedArgsText: event.args ?? "",
                      status: "streaming",
                    },
                  ],
                };
              }

              const current = toolCalls[targetIndex];
              toolCalls[targetIndex] = {
                ...current,
                name: event.name ?? current.name,
                callId: event.id ?? current.callId,
                streamedArgsText: `${current.streamedArgsText}${event.args ?? ""}`,
                status:
                  current.status === "completed" ? "completed" : "streaming",
              };

              if (!knownKey) {
                if (streamIndex !== null) {
                  streamStateRef.current.toolKeysByIndex.set(
                    streamIndex,
                    toolCalls[targetIndex].key,
                  );
                }
              }

              if (event.id && toolCalls[targetIndex].key) {
                streamStateRef.current.toolKeysByCallId.set(
                  event.id,
                  toolCalls[targetIndex].key,
                );
              }

              return {
                ...turn,
                toolCalls,
              };
            });
            return;
          }

          if (event.type === "tool_call") {
            const turnId = ensureActiveAssistantTurn();
            const mappedKey = event.id?.trim()
              ? streamStateRef.current.toolKeysByCallId.get(event.id)
              : undefined;
            updateAssistantTurn(turnId, (turn) => {
              const toolCalls = turn.toolCalls.slice();
              let targetIndex = mappedKey
                ? toolCalls.findIndex((item) => item.key === mappedKey)
                : -1;

              if (targetIndex < 0) {
                targetIndex = event.id
                  ? toolCalls.findIndex((item) => item.callId === event.id)
                  : -1;
              }

              if (targetIndex < 0) {
                targetIndex = toolCalls.findIndex(
                  (item) =>
                    item.status === "streaming" && item.name === "unknown",
                );
              }

              if (targetIndex < 0) {
                targetIndex = toolCalls.findIndex(
                  (item) => item.status === "streaming",
                );
              }

              if (targetIndex < 0) {
                targetIndex = toolCalls.findIndex(
                  (item) =>
                    item.status === "called" &&
                    !item.resultContent &&
                    (event.name ? item.name === event.name : true),
                );
              }

              const argsText = Object.keys(event.args).length
                ? JSON.stringify(event.args, null, 2)
                : "";

              if (targetIndex < 0) {
                toolCalls.push({
                  key: event.id
                    ? `${turn.id}:call:${event.id}`
                    : `${turn.id}:tool:${streamStateRef.current.nextToolSeq++}`,
                  name: event.name ?? "unknown",
                  callType: event.call_type,
                  callId: event.id,
                  streamedArgsText: argsText,
                  finalArgs: event.args,
                  status: "called",
                });
              } else {
                const current = toolCalls[targetIndex];
                toolCalls[targetIndex] = {
                  ...current,
                  name: event.name ?? current.name,
                  callType: event.call_type ?? current.callType,
                  callId: event.id ?? current.callId,
                  finalArgs: event.args,
                  streamedArgsText: current.streamedArgsText || argsText,
                  status:
                    current.status === "completed" ? "completed" : "called",
                };
              }

              if (event.id) {
                streamStateRef.current.toolKeysByCallId.set(
                  event.id,
                  toolCalls[targetIndex].key,
                );
              }

              return {
                ...turn,
                toolCalls,
              };
            });
            return;
          }

          if (event.type === "tool_result") {
            const attachments =
              event.artifacts?.map((artifact) => ({
                id: artifact.id,
                filename: artifact.filename,
                contentType: artifact.content_type,
                mediaType: artifact.media_type,
                sizeBytes: artifact.size_bytes,
                previewText: artifact.preview_text,
                extractionNote: artifact.extraction_note,
                localPreviewUrl:
                  artifact.media_type === "image"
                    ? buildUrl(artifact.download_url)
                    : undefined,
              })) ?? [];

            const turnId = ensureActiveAssistantTurn();
            updateAssistantTurn(turnId, (turn) => {
              const toolCalls = turn.toolCalls.slice();
              const mappedKey = event.tool_call_id?.trim()
                ? streamStateRef.current.toolKeysByCallId.get(
                    event.tool_call_id,
                  )
                : undefined;
              let targetIndex = mappedKey
                ? toolCalls.findIndex((item) => item.key === mappedKey)
                : -1;

              if (targetIndex < 0) {
                targetIndex = event.tool_call_id
                  ? toolCalls.findIndex(
                      (item) => item.callId === event.tool_call_id,
                    )
                  : -1;
              }

              if (targetIndex < 0) {
                targetIndex = toolCalls.findIndex(
                  (item) => !item.resultContent,
                );
              }

              if (targetIndex < 0) {
                toolCalls.push({
                  key: event.tool_call_id
                    ? `${turn.id}:result:${event.tool_call_id}`
                    : `${turn.id}:tool:${streamStateRef.current.nextToolSeq++}`,
                  name: "unknown",
                  callId: event.tool_call_id,
                  streamedArgsText: "",
                  status: "called",
                });
                targetIndex = toolCalls.length - 1;
              }

              const current = toolCalls[targetIndex];
              toolCalls[targetIndex] = {
                ...current,
                callId: current.callId ?? event.tool_call_id,
                resultContent: event.content,
                resultArtifacts: attachments,
                status: "completed",
              };

              if (event.tool_call_id) {
                streamStateRef.current.toolKeysByCallId.set(
                  event.tool_call_id,
                  toolCalls[targetIndex].key,
                );
              }

              return {
                ...turn,
                toolCalls,
                attachments: mergeAttachments(turn.attachments, attachments),
              };
            });
            return;
          }

          if (event.type === "sandbox_status") {
            const turnId = ensureActiveAssistantTurn();
            const nextText = formatSandboxStatus(event);
            updateAssistantTurn(turnId, (turn) => {
              const notes = turn.notes.slice();
              const existingIndex =
                streamStateRef.current.sandboxNoteIndexByRunId.get(
                  event.run_id,
                );
              if (existingIndex === undefined) {
                notes.push(nextText);
                streamStateRef.current.sandboxNoteIndexByRunId.set(
                  event.run_id,
                  notes.length - 1,
                );
              } else {
                notes[existingIndex] = nextText;
              }
              return {
                ...turn,
                notes,
              };
            });
            return;
          }

          if (event.type === "final") {
            const turnId = ensureActiveAssistantTurn();
            updateAssistantTurn(turnId, (turn) => {
              const usage = isRecord(event.usage) ? event.usage : null;
              const responseMetadata = isRecord(event.response_metadata)
                ? event.response_metadata
                : null;
              return {
                ...turn,
                answerText: event.output_text,
                usage,
                responseMetadata,
                reasoningTokens: extractReasoningTokens(usage),
                time: formatTime(new Date()),
              };
            });

            if (
              event.conversation_id &&
              event.conversation_id !== activeChatId
            ) {
              router.replace(`/c/${event.conversation_id}`);
            }

            window.dispatchEvent(new Event("agent-conversations:refresh"));
            setIsTyping(false);
          }
        },
      });
    } catch (error) {
      if (abortController.signal.aborted) {
        return;
      }
      setIsTyping(false);
      addAssistantNote(
        error instanceof Error
          ? `Something went wrong: ${error.message}`
          : "Something went wrong while streaming the response.",
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
          <ChatEmptyState actions={quickActions} onAction={handleQuickAction} />
        ) : (
          <ChatMessages timeline={timeline} isTyping={isTyping} />
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
