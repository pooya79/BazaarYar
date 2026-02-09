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
  sandboxNoteIndexByRunId: Map<string, number>;
  nextToolSeq: number;
};

const initialStreamState = (): StreamState => ({
  assistantTurnId: null,
  toolKeysByIndex: new Map(),
  toolKeysByCallId: new Map(),
  sandboxNoteIndexByRunId: new Map(),
  nextToolSeq: 0,
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

export function useChatStream({
  activeChatId,
  setTimeline,
  createLocalId,
  createAssistantTurn,
  onConversationRedirect,
}: UseChatStreamParams) {
  const [isTyping, setIsTyping] = useState(false);
  const streamAbortRef = useRef<AbortController | null>(null);
  const streamStateRef = useRef<StreamState>(initialStreamState());
  const hasStreamedRef = useRef(false);

  const resetStreamState = useCallback(() => {
    streamStateRef.current = initialStreamState();
    hasStreamedRef.current = false;
  }, []);

  const abortStream = useCallback(() => {
    streamAbortRef.current?.abort();
    streamAbortRef.current = null;
    setIsTyping(false);
    resetStreamState();
  }, [resetStreamState]);

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
    [createAssistantTurn, setTimeline],
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

  const startStream = useCallback(
    async ({
      message,
      conversationId,
      attachmentIds,
    }: StartChatStreamParams) => {
      abortStream();

      const abortController = new AbortController();
      streamAbortRef.current = abortController;
      setIsTyping(true);

      try {
        await streamAgent({
          message,
          conversationId,
          attachmentIds,
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
                    streamStateRef.current.toolKeysByIndex.set(
                      streamIndex,
                      key,
                    );
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
                onConversationRedirect(event.conversation_id);
              }

              window.dispatchEvent(new Event("agent-conversations:refresh"));
              setIsTyping(false);
              resetStreamState();
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
    },
    [
      abortStream,
      activeChatId,
      addAssistantNote,
      appendAssistantAnswer,
      appendAssistantReasoning,
      ensureActiveAssistantTurn,
      onConversationRedirect,
      resetStreamState,
      updateAssistantTurn,
    ],
  );

  return {
    isTyping,
    abortStream,
    addAssistantNote,
    addUserMessage,
    startStream,
  };
}
