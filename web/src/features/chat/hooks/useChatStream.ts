import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import type {
  AssistantTurn,
  ChatTimelineItem,
  MessageAttachment,
} from "@/features/chat/model/types";
import {
  extractReasoningTokens,
  formatSandboxStatus,
  formatTime,
} from "@/features/chat/utils/chatViewUtils";
import { streamAgent } from "@/shared/api/clients/agent.client";
import { buildUrl } from "@/shared/api/http";

type UseChatStreamParams = {
  activeChatId: string | null;
  setTimeline: Dispatch<SetStateAction<ChatTimelineItem[]>>;
  createLocalId: () => string;
  createAssistantTurn: () => AssistantTurn;
  onConversationRedirect: (conversationId: string) => void;
};

type StartChatStreamParams = {
  message: string;
  conversationId: string | null;
  attachmentIds: string[];
};

type StreamState = {
  assistantTurnId: string | null;
  toolKeysByIndex: Map<number, string>;
  toolKeysByCallId: Map<string, string>;
  sandboxNoteBlockIdByRunId: Map<string, string>;
  nextToolSeq: number;
  nextBlockSeq: number;
  activeTextBlockId: string | null;
  activeReasoningBlockId: string | null;
};

const initialStreamState = (): StreamState => ({
  assistantTurnId: null,
  toolKeysByIndex: new Map(),
  toolKeysByCallId: new Map(),
  sandboxNoteBlockIdByRunId: new Map(),
  nextToolSeq: 0,
  nextBlockSeq: 0,
  activeTextBlockId: null,
  activeReasoningBlockId: null,
});

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

function blockId(turnId: string, type: string, seq: number) {
  return `${turnId}:block:${type}:${seq}`;
}

export function useChatStream({
  activeChatId,
  setTimeline,
  createLocalId,
  createAssistantTurn,
  onConversationRedirect,
}: UseChatStreamParams) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [isWaitingForFirstChunk, setIsWaitingForFirstChunk] = useState(false);
  const streamAbortRef = useRef<AbortController | null>(null);
  const streamStateRef = useRef<StreamState>(initialStreamState());
  const hasReceivedStreamPayloadRef = useRef(false);
  const streamConversationIdRef = useRef<string | null>(null);

  const resetStreamState = useCallback(() => {
    streamStateRef.current = initialStreamState();
    hasReceivedStreamPayloadRef.current = false;
    setIsWaitingForFirstChunk(false);
  }, []);

  const clearStreamTracking = useCallback(() => {
    resetStreamState();
    streamConversationIdRef.current = null;
    setIsStreaming(false);
  }, [resetStreamState]);

  const abortStream = useCallback(() => {
    streamAbortRef.current?.abort();
    streamAbortRef.current = null;
    clearStreamTracking();
  }, [clearStreamTracking]);

  const stopStream = useCallback(() => {
    const pendingConversationId = streamConversationIdRef.current;
    const activeAbortController = streamAbortRef.current;
    if (!activeAbortController && !pendingConversationId) {
      return;
    }

    activeAbortController?.abort();
    streamAbortRef.current = null;
    clearStreamTracking();
    window.dispatchEvent(new Event("agent-conversations:refresh"));

    if (!activeChatId && pendingConversationId) {
      onConversationRedirect(pendingConversationId);
    }
  }, [activeChatId, clearStreamTracking, onConversationRedirect]);

  useEffect(() => {
    return () => {
      abortStream();
    };
  }, [abortStream]);

  useEffect(() => {
    const handleReset = () => {
      abortStream();
    };

    window.addEventListener("agent-chat:reset", handleReset);
    return () => {
      window.removeEventListener("agent-chat:reset", handleReset);
    };
  }, [abortStream]);

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
    [setTimeline],
  );

  const ensureActiveAssistantTurn = useCallback(() => {
    const activeTurnId = streamStateRef.current.assistantTurnId;
    if (activeTurnId) {
      return activeTurnId;
    }

    const turn = createAssistantTurn();
    setTimeline((prev) => [...prev, turn]);
    streamStateRef.current.assistantTurnId = turn.id;
    return turn.id;
  }, [createAssistantTurn, setTimeline]);

  const pushAssistantBlock = useCallback(
    (
      turn: AssistantTurn,
      type: "text" | "reasoning" | "note",
      content: string,
      blockIdValue?: string,
    ) => {
      const id =
        blockIdValue ??
        blockId(turn.id, type, streamStateRef.current.nextBlockSeq++);
      return {
        ...turn,
        blocks: [...turn.blocks, { id, type, content }],
      };
    },
    [],
  );

  const closeStreamTextPhases = useCallback(() => {
    streamStateRef.current.activeTextBlockId = null;
    streamStateRef.current.activeReasoningBlockId = null;
  }, []);

  const appendAssistantTextBlock = useCallback(
    (type: "text" | "reasoning", chunk: string) => {
      if (!chunk) {
        return;
      }

      const turnId = ensureActiveAssistantTurn();
      updateAssistantTurn(turnId, (turn) => {
        const state = streamStateRef.current;
        const targetId =
          type === "text"
            ? state.activeTextBlockId
            : state.activeReasoningBlockId;

        if (targetId) {
          const targetIndex = turn.blocks.findIndex(
            (block) => block.id === targetId,
          );
          if (targetIndex >= 0) {
            const existing = turn.blocks[targetIndex];
            if (existing.type === type) {
              const nextBlocks = turn.blocks.slice();
              nextBlocks[targetIndex] = {
                ...existing,
                content: `${existing.content}${chunk}`,
              };
              return {
                ...turn,
                blocks: nextBlocks,
              };
            }
          }
        }

        const newId = blockId(turn.id, type, state.nextBlockSeq++);
        if (type === "text") {
          state.activeTextBlockId = newId;
          state.activeReasoningBlockId = null;
        } else {
          state.activeReasoningBlockId = newId;
          state.activeTextBlockId = null;
        }

        return {
          ...turn,
          blocks: [...turn.blocks, { id: newId, type, content: chunk }],
        };
      });
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
            return pushAssistantBlock(item, "note", note);
          });
        }

        const turn = createAssistantTurn();
        return [...prev, pushAssistantBlock(turn, "note", note)];
      });
    },
    [createAssistantTurn, pushAssistantBlock, setTimeline],
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
    [createLocalId, setTimeline],
  );

  const ensureToolBlock = useCallback(
    (turn: AssistantTurn, toolKey: string) => {
      if (
        turn.blocks.some(
          (block) => block.type === "tool_call" && block.toolKey === toolKey,
        )
      ) {
        return turn;
      }
      return {
        ...turn,
        blocks: [
          ...turn.blocks,
          {
            id: blockId(turn.id, "tool", streamStateRef.current.nextBlockSeq++),
            type: "tool_call",
            toolKey,
          },
        ],
      };
    },
    [],
  );

  const startStream = useCallback(
    async ({
      message,
      conversationId,
      attachmentIds,
    }: StartChatStreamParams) => {
      abortStream();

      const abortController = new AbortController();
      streamAbortRef.current = abortController;
      setIsStreaming(true);
      setIsWaitingForFirstChunk(true);

      try {
        await streamAgent({
          message,
          conversationId,
          attachmentIds,
          signal: abortController.signal,
          onEvent: (event) => {
            if (event.type === "conversation") {
              streamConversationIdRef.current = event.conversation_id;
              return;
            }

            if (!hasReceivedStreamPayloadRef.current) {
              setIsWaitingForFirstChunk(false);
              hasReceivedStreamPayloadRef.current = true;
            }

            if (event.type === "text_delta") {
              streamStateRef.current.activeReasoningBlockId = null;
              appendAssistantTextBlock("text", event.content);
              return;
            }

            if (event.type === "reasoning_delta") {
              streamStateRef.current.activeTextBlockId = null;
              appendAssistantTextBlock("reasoning", event.content);
              return;
            }

            if (event.type === "tool_call_delta") {
              closeStreamTextPhases();
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
                    streamStateRef.current.toolKeysByIndex.set(
                      streamIndex,
                      key,
                    );
                  }
                  if (event.id) {
                    streamStateRef.current.toolKeysByCallId.set(event.id, key);
                  }

                  return ensureToolBlock(
                    {
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
                    },
                    key,
                  );
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

                if (!knownKey && streamIndex !== null) {
                  streamStateRef.current.toolKeysByIndex.set(
                    streamIndex,
                    toolCalls[targetIndex].key,
                  );
                }

                if (event.id && toolCalls[targetIndex].key) {
                  streamStateRef.current.toolKeysByCallId.set(
                    event.id,
                    toolCalls[targetIndex].key,
                  );
                }

                return ensureToolBlock(
                  {
                    ...turn,
                    toolCalls,
                  },
                  toolCalls[targetIndex].key,
                );
              });
              return;
            }

            if (event.type === "tool_call") {
              closeStreamTextPhases();
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
                  targetIndex = toolCalls.length - 1;
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

                return ensureToolBlock(
                  {
                    ...turn,
                    toolCalls,
                  },
                  toolCalls[targetIndex].key,
                );
              });
              return;
            }

            if (event.type === "tool_result") {
              closeStreamTextPhases();
              const attachments =
                event.artifacts?.map((artifact) => ({
                  id: artifact.id,
                  filename: artifact.filename,
                  contentType: artifact.content_type,
                  mediaType: artifact.media_type,
                  sizeBytes: artifact.size_bytes,
                  previewText: artifact.preview_text,
                  extractionNote: artifact.extraction_note,
                  downloadUrl: buildUrl(artifact.download_url),
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
                  resultPayload: event.payload ?? current.resultPayload,
                  resultArtifacts: attachments,
                  status: "completed",
                };

                if (event.tool_call_id) {
                  streamStateRef.current.toolKeysByCallId.set(
                    event.tool_call_id,
                    toolCalls[targetIndex].key,
                  );
                }

                return ensureToolBlock(
                  {
                    ...turn,
                    toolCalls,
                    attachments: mergeAttachments(
                      turn.attachments,
                      attachments,
                    ),
                  },
                  toolCalls[targetIndex].key,
                );
              });
              return;
            }

            if (event.type === "sandbox_status") {
              closeStreamTextPhases();
              const turnId = ensureActiveAssistantTurn();
              const nextText = formatSandboxStatus(event);
              updateAssistantTurn(turnId, (turn) => {
                const noteBlockId =
                  streamStateRef.current.sandboxNoteBlockIdByRunId.get(
                    event.run_id,
                  );
                if (!noteBlockId) {
                  const newBlockId = blockId(
                    turn.id,
                    "note",
                    streamStateRef.current.nextBlockSeq++,
                  );
                  streamStateRef.current.sandboxNoteBlockIdByRunId.set(
                    event.run_id,
                    newBlockId,
                  );
                  return {
                    ...turn,
                    blocks: [
                      ...turn.blocks,
                      { id: newBlockId, type: "note", content: nextText },
                    ],
                  };
                }

                const noteIndex = turn.blocks.findIndex(
                  (block) => block.id === noteBlockId,
                );
                if (noteIndex < 0) {
                  return turn;
                }

                const nextBlocks = turn.blocks.slice();
                const current = nextBlocks[noteIndex];
                if (current.type !== "note") {
                  return turn;
                }

                nextBlocks[noteIndex] = {
                  ...current,
                  content: nextText,
                };
                return {
                  ...turn,
                  blocks: nextBlocks,
                };
              });
              return;
            }

            if (event.type === "final") {
              closeStreamTextPhases();
              const turnId = ensureActiveAssistantTurn();
              updateAssistantTurn(turnId, (turn) => {
                const usage = isRecord(event.usage) ? event.usage : null;
                const responseMetadata = isRecord(event.response_metadata)
                  ? event.response_metadata
                  : null;
                const extractedReasoning = extractReasoningTokens(usage);

                const hasTextBlock = turn.blocks.some(
                  (block) =>
                    block.type === "text" && block.content.trim().length > 0,
                );
                const shouldAppendFinalText =
                  !hasTextBlock && Boolean(event.output_text.trim());

                const nextBlocks = shouldAppendFinalText
                  ? [
                      ...turn.blocks,
                      {
                        id: blockId(
                          turn.id,
                          "text",
                          streamStateRef.current.nextBlockSeq++,
                        ),
                        type: "text" as const,
                        content: event.output_text,
                      },
                    ]
                  : turn.blocks;

                return {
                  ...turn,
                  blocks: nextBlocks,
                  usage,
                  responseMetadata,
                  reasoningTokens:
                    extractedReasoning ?? turn.reasoningTokens ?? null,
                  time: formatTime(new Date()),
                };
              });

              const resolvedConversationId =
                event.conversation_id || streamConversationIdRef.current;
              if (
                resolvedConversationId &&
                resolvedConversationId !== activeChatId
              ) {
                onConversationRedirect(resolvedConversationId);
              }

              window.dispatchEvent(new Event("agent-conversations:refresh"));
              clearStreamTracking();
            }
          },
        });
      } catch (error) {
        if (abortController.signal.aborted) {
          return;
        }

        clearStreamTracking();
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
    },
    [
      abortStream,
      activeChatId,
      addAssistantNote,
      appendAssistantTextBlock,
      closeStreamTextPhases,
      ensureActiveAssistantTurn,
      ensureToolBlock,
      onConversationRedirect,
      clearStreamTracking,
      updateAssistantTurn,
    ],
  );

  const showTypingIndicator = isStreaming && isWaitingForFirstChunk;

  return {
    isStreaming,
    isWaitingForFirstChunk,
    showTypingIndicator,
    abortStream,
    stopStream,
    addAssistantNote,
    addUserMessage,
    startStream,
  };
}
