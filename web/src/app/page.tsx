"use client";

import { cn } from "@/lib/utils";
import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import {
  brandVoices,
  botResponses,
  initialChats,
  library,
  quickActions,
  tools,
} from "@/components/marketing/constants";
import { MarketingEmptyState } from "@/components/marketing/MarketingEmptyState";
import { MarketingHeader } from "@/components/marketing/MarketingHeader";
import { MarketingInput } from "@/components/marketing/MarketingInput";
import { MarketingMessages } from "@/components/marketing/MarketingMessages";
import { MarketingSidebar } from "@/components/marketing/MarketingSidebar";
import type {
  ChatAction,
  ChatItem,
  Message,
  Sender,
} from "@/components/marketing/types";

function formatTime(date: Date) {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [chatsOpen, setChatsOpen] = useState(false);
  const [activeTool, setActiveTool] = useState("assistant");
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [chatItems, setChatItems] = useState<ChatItem[]>(initialChats);
  const [chatMenuOpenId, setChatMenuOpenId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [messageInput, setMessageInput] = useState("");
  const [brandVoiceIndex, setBrandVoiceIndex] = useState(0);
  const messageId = useRef(0);
  const typingTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const chatWrapperRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
    chatWrapperRef.current.scrollTop = chatWrapperRef.current.scrollHeight;
  }, [messages, isTyping]);

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
      if (typingTimeout.current) {
        clearTimeout(typingTimeout.current);
      }
    };
  }, []);

  const addMessage = (text: string, sender: Sender) => {
    const nextMessage: Message = {
      id: messageId.current++,
      sender,
      text,
      time: formatTime(new Date()),
    };
    setMessages((prev) => [...prev, nextMessage]);
  };

  const startConversation = (text: string) => {
    if (typingTimeout.current) {
      clearTimeout(typingTimeout.current);
    }
    setIsTyping(false);
    const firstMessage: Message = {
      id: messageId.current++,
      sender: "bot",
      text,
      time: formatTime(new Date()),
    };
    setMessages([firstMessage]);
  };

  const handleSend = (overrideText?: string) => {
    const text = (overrideText ?? messageInput).trim();
    if (!text) return;

    addMessage(text, "user");
    setMessageInput("");

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    setIsTyping(true);
    typingTimeout.current = setTimeout(() => {
      const response = botResponses[Math.floor(Math.random() * botResponses.length)];
      setIsTyping(false);
      addMessage(response, "bot");
    }, 1400 + Math.random() * 900);
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
    startConversation(`Loaded chat: ${chat.title}. How can I help you next?`);
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
          item.id === chatId ? { ...item, title: nextTitle.trim() } : item
        )
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
          item.id === chatId ? { ...item, starred: !item.starred } : item
        )
      );
      setChatMenuOpenId(null);
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

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--marketing-bg)] font-sans text-[var(--marketing-text-primary)]">
      <div
        className={cn(
          "fixed inset-0 z-[99] bg-[var(--marketing-overlay)] backdrop-blur-[4px] md:hidden",
          sidebarOpen ? "block" : "hidden"
        )}
        onClick={() => setSidebarOpen(false)}
      />

      <MarketingSidebar
        isOpen={sidebarOpen}
        chatsOpen={chatsOpen}
        onToggleChats={() => setChatsOpen((prev) => !prev)}
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

      <main className="relative flex flex-1 flex-col overflow-hidden bg-[var(--marketing-bg)]">
        <MarketingHeader
          pageTitle={pageTitle}
          PageIcon={PageIcon}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((prev) => !prev)}
        />

        <div className="flex flex-1 flex-col overflow-y-auto p-4 md:p-8" ref={chatWrapperRef}>
          {!hasMessages ? (
            <MarketingEmptyState actions={quickActions} onAction={handleQuickAction} />
          ) : (
            <MarketingMessages messages={messages} isTyping={isTyping} />
          )}
        </div>

        <MarketingInput
          textareaRef={textareaRef}
          value={messageInput}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onSend={handleSend}
          brandVoice={brandVoices[brandVoiceIndex]}
          onToggleBrandVoice={toggleBrandVoice}
        />
      </main>
    </div>
  );
}
