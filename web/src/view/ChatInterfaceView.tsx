"use client";

import type { KeyboardEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  brandVoices,
  initialChats,
  library,
  quickActions,
  tools,
} from "@/components/chat-interface/constants";
import { ChatEmptyState } from "@/components/chat-interface/ChatEmptyState";
import { ChatHeader } from "@/components/chat-interface/ChatHeader";
import { ChatInput } from "@/components/chat-interface/ChatInput";
import { ChatMessages } from "@/components/chat-interface/ChatMessages";
import { ChatSidebar } from "@/components/sidebar/ChatSidebar";
import type {
  ChatAction,
  ChatItem,
  Message,
} from "@/components/chat-interface/types";
import { streamAgent } from "@/lib/api/clients/agent.client";
import { cn } from "@/lib/utils";
import type {
  ReferenceTable,
  ReferenceTableAction,
} from "@/view/ReferenceTablesView";
import {
  initialReferenceTables,
  ReferenceTablesView,
} from "@/view/ReferenceTablesView";

function formatTime(date: Date) {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function ChatInterfaceView() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [chatsOpen, setChatsOpen] = useState(false);
  const [activeTool, setActiveTool] = useState("assistant");
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [chatItems, setChatItems] = useState<ChatItem[]>(initialChats);
  const [chatMenuOpenId, setChatMenuOpenId] = useState<string | null>(null);
  const [referenceTables, setReferenceTables] = useState<ReferenceTable[]>(
    initialReferenceTables,
  );
  const [tableMenuOpenId, setTableMenuOpenId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [messageInput, setMessageInput] = useState("");
  const [brandVoiceIndex, setBrandVoiceIndex] = useState(0);
  const messageId = useRef(0);
  const chatWrapperRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const referenceTableCounter = useRef(1);
  const streamAbortRef = useRef<AbortController | null>(null);
  const streamStateRef = useRef({
    textId: null as number | null,
    reasoningId: null as number | null,
    toolDelta: new Map<
      number,
      { id: number; name?: string; args?: string; callId?: string }
    >(),
  });
  const historyRef = useRef<{ role: "user" | "assistant"; content: string }[]>(
    [],
  );
  const hasStreamedRef = useRef(false);

  const { pageTitle, pageIcon: PageIcon } = useMemo(() => {
    const allItems = [...tools, ...library];
    const match = allItems.find((item) => item.id === activeTool) ?? tools[0];
    return {
      pageTitle: match.label,
      pageIcon: match.icon,
    };
  }, [activeTool]);

  useEffect(() => {
    if (!chatWrapperRef.current) return;
    if (messages.length === 0 && !isTyping) return;
    chatWrapperRef.current.scrollTop = chatWrapperRef.current.scrollHeight;
  }, [messages.length, isTyping]);

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth <= 768) {
        setSidebarOpen(false);
      }
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    return () => {
      streamAbortRef.current?.abort();
    };
  }, []);

  const addMessage = (
    text: string,
    sender: Message["sender"],
    kind?: Message["kind"],
  ) => {
    const nextMessage: Message = {
      id: messageId.current++,
      sender,
      text,
      time: formatTime(new Date()),
      kind,
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

  const formatMetaBlock = (label: string, payload: unknown) => {
    if (payload === null || payload === undefined) {
      return "";
    }
    if (typeof payload === "string") {
      return `${label}\n${payload}`;
    }
    try {
      return `${label}\n${JSON.stringify(payload, null, 2)}`;
    } catch {
      return `${label}\n${String(payload)}`;
    }
  };

  const formatToolDelta = (entry: {
    name?: string;
    args?: string;
    callId?: string;
  }) => {
    // Tool deltas can arrive as partial JSON, so keep raw args and add a header.
    const headerParts = [`name: ${entry.name ?? "unknown"}`];
    if (entry.callId) {
      headerParts.push(`id: ${entry.callId}`);
    }
    const header = headerParts.join(" | ");
    return entry.args ? `${header}\n${entry.args}` : header;
  };

  const formatToolCall = (event: {
    name?: string | null;
    id?: string | null;
    call_type?: string | null;
    args?: Record<string, unknown>;
  }) => {
    const lines = [`name: ${event.name ?? "unknown"}`];
    if (event.call_type) {
      lines.push(`call_type: ${event.call_type}`);
    }
    if (event.id) {
      lines.push(`id: ${event.id}`);
    }
    if (event.args) {
      lines.push("args:");
      lines.push(JSON.stringify(event.args, null, 2));
    }
    return lines.join("\n");
  };

  const formatToolResult = (event: {
    tool_call_id?: string | null;
    content: string;
  }) => {
    const lines = [];
    if (event.tool_call_id) {
      lines.push(`tool_call_id: ${event.tool_call_id}`);
    }
    lines.push(event.content);
    return lines.join("\n");
  };

  const resetStreamState = () => {
    streamStateRef.current = {
      textId: null,
      reasoningId: null,
      toolDelta: new Map(),
    };
    hasStreamedRef.current = false;
  };

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

  const startConversation = (text: string) => {
    setIsTyping(false);
    const firstMessage: Message = {
      id: messageId.current++,
      sender: "bot",
      text,
      time: formatTime(new Date()),
      kind: "assistant",
    };
    setMessages([firstMessage]);
  };

  const handleSend = async (overrideText?: string) => {
    const baseText =
      typeof overrideText === "string" ? overrideText : messageInput;
    const text = baseText.trim();
    if (!text) return;

    streamAbortRef.current?.abort();
    resetStreamState();

    addMessage(text, "user");
    setMessageInput("");

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    setIsTyping(true);

    const historySnapshot = historyRef.current;
    historyRef.current = [...historySnapshot, { role: "user", content: text }];

    const abortController = new AbortController();
    streamAbortRef.current = abortController;

    try {
      await streamAgent({
        message: text,
        history: historySnapshot,
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
            if (event.output_text) {
              historyRef.current = [
                ...historyRef.current,
                { role: "assistant", content: event.output_text },
              ];
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

  const handleToolClick = (toolId: string) => {
    setActiveTool(toolId);
    if (window.innerWidth <= 768) {
      setSidebarOpen(false);
    }
  };

  const handleChatSelect = (chatId: string) => {
    const chat = chatItems.find((item) => item.id === chatId);
    if (!chat) return;
    setActiveChatId(chatId);
    setChatMenuOpenId(null);
    historyRef.current = [];
    startConversation(`Loaded chat: ${chat.title}. How can I help you next?`);
  };

  const handleNewChat = () => {
    streamAbortRef.current?.abort();
    setIsTyping(false);
    setMessages([]);
    setMessageInput("");
    setActiveChatId(null);
    setChatMenuOpenId(null);
    setActiveTool("assistant");
    historyRef.current = [];
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleChatAction = (action: ChatAction, chatId: string) => {
    if (action === "use") {
      handleChatSelect(chatId);
      setChatMenuOpenId(null);
      return;
    }

    if (action === "rename") {
      const current = chatItems.find((item) => item.id === chatId);
      if (!current) return;
      const nextTitle = window.prompt("Rename chat", current.title);
      if (!nextTitle || !nextTitle.trim()) return;
      setChatItems((prev) =>
        prev.map((item) =>
          item.id === chatId ? { ...item, title: nextTitle.trim() } : item,
        ),
      );
      setChatMenuOpenId(null);
      return;
    }

    if (action === "delete") {
      setChatItems((prev) => prev.filter((item) => item.id !== chatId));
      setChatMenuOpenId(null);
      if (activeChatId === chatId) {
        setActiveChatId(null);
        setMessages([]);
      }
      return;
    }

    if (action === "star") {
      setChatItems((prev) =>
        prev.map((item) =>
          item.id === chatId ? { ...item, starred: !item.starred } : item,
        ),
      );
      setChatMenuOpenId(null);
    }
  };

  const handleQuickAction = (prompt: string) => {
    handleSend(prompt);
  };

  const handleAddReferenceTable = () => {
    const nextIndex = referenceTableCounter.current++;
    const nextTable: ReferenceTable = {
      id: `reference-${Date.now()}-${nextIndex}`,
      name: `Reference Table ${nextIndex}`,
      description: "Define approved values agents should rely on.",
      rows: 0,
      columns: 4,
      source: "Manual entry",
      refresh: "On demand",
      updatedAt: "Just now",
      status: "active",
      assignedAgents: [],
      tags: ["draft"],
    };
    setReferenceTables((prev) => [nextTable, ...prev]);
  };

  const handleReferenceTableAction = (
    action: ReferenceTableAction,
    tableId: string,
  ) => {
    if (action === "toggle") {
      setReferenceTables((prev) =>
        prev.map((table) =>
          table.id === tableId
            ? {
                ...table,
                status: table.status === "active" ? "disabled" : "active",
              }
            : table,
        ),
      );
      setTableMenuOpenId(null);
      return;
    }

    if (action === "remove") {
      setReferenceTables((prev) =>
        prev.map((table) =>
          table.id === tableId ? { ...table, assignedAgents: [] } : table,
        ),
      );
      setTableMenuOpenId(null);
      return;
    }

    if (action === "delete") {
      setReferenceTables((prev) =>
        prev.filter((table) => table.id !== tableId),
      );
      setTableMenuOpenId(null);
    }
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

  const isReferenceTables = activeTool === "reference-tables";
  const hasMessages = messages.length > 0;

  return (
    <div className="flex h-screen overflow-hidden bg-marketing-bg font-sans text-marketing-text-primary">
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
        tools={tools}
        library={library}
        activeTool={activeTool}
        onToolSelect={handleToolClick}
      />

      <main className="relative flex flex-1 flex-col overflow-hidden bg-marketing-bg">
        <ChatHeader
          pageTitle={pageTitle}
          PageIcon={PageIcon}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
        />

        {isReferenceTables ? (
          <ReferenceTablesView
            tables={referenceTables}
            tableMenuOpenId={tableMenuOpenId}
            onTableMenuOpenChange={setTableMenuOpenId}
            onAddTable={handleAddReferenceTable}
            onTableAction={handleReferenceTableAction}
          />
        ) : (
          <>
            <div
              className="flex flex-1 flex-col overflow-y-auto p-4 md:p-8"
              ref={chatWrapperRef}
            >
              {!hasMessages ? (
                <ChatEmptyState
                  actions={quickActions}
                  onAction={handleQuickAction}
                />
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
              brandVoice={brandVoices[brandVoiceIndex]}
              onToggleBrandVoice={toggleBrandVoice}
            />
          </>
        )}
      </main>
    </div>
  );
}
