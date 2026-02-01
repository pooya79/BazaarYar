"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  BarChart3,
  BookOpen,
  Calendar,
  ChevronDown,
  Clock,
  Menu,
  Mail,
  MessageSquare,
  Mic,
  MoreHorizontal,
  Palette,
  Paperclip,
  PenLine,
  Rocket,
  Search,
  SendHorizontal,
  Settings,
  Share2,
  Smartphone,
  Sparkles,
  Target,
  Trash2,
  User,
  X,
  Star,
  PencilLine,
} from "lucide-react";

type Sender = "bot" | "user";

type Message = {
  id: number;
  sender: Sender;
  text: string;
  time: string;
};

type ChatItem = {
  id: string;
  title: string;
  meta: string;
  statusClass: string;
  starred: boolean;
};

const tools = [
  { id: "assistant", label: "Chat", icon: MessageSquare },
  { id: "content", label: "Content Studio", icon: PenLine },
  { id: "seo", label: "SEO Keywords", icon: BarChart3 },
  { id: "email", label: "Email Campaigns", icon: Mail },
  { id: "social", label: "Social Media", icon: Smartphone },
  { id: "ads", label: "Ad Copy", icon: Target },
];

const library = [
  { id: "guidelines", label: "Brand Guidelines", icon: BookOpen },
  { id: "assets", label: "Asset Library", icon: Palette },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
];

const initialChats: ChatItem[] = [
  {
    id: "launch",
    title: "Product Launch Support",
    meta: "Active - 12 messages",
    statusClass: "status-active",
    starred: true,
  },
  {
    id: "audit",
    title: "SEO Audit Questions",
    meta: "Draft - 3 messages",
    statusClass: "status-draft",
    starred: false,
  },
  {
    id: "social",
    title: "Social Calendar Ideas",
    meta: "Active - 8 messages",
    statusClass: "status-active",
    starred: false,
  },
];

const quickActions = [
  {
    title: "Generate Ad Copy",
    description: "Create high-converting ads for Google, Facebook, or LinkedIn",
    icon: Target,
    prompt: "Write Google Ads for a fitness app targeting millennials",
  },
  {
    title: "Content Calendar",
    description: "Plan your social media and blog content strategy",
    icon: Calendar,
    prompt: "Create a content calendar for a B2B SaaS company",
  },
  {
    title: "SEO Optimization",
    description: "Improve rankings with keyword suggestions and meta tags",
    icon: Search,
    prompt: "Optimize this headline for SEO: Best Coffee Makers 2024",
  },
  {
    title: "Email Sequence",
    description: "Build nurture campaigns and newsletters",
    icon: Mail,
    prompt: "Write a welcome email series for new subscribers",
  },
];

const botResponses = [
  "Great brief! I'll create conversion-focused copy that highlights your USPs while maintaining a professional yet approachable tone. Here are three variations...",
  "Perfect! Based on current trends, I recommend focusing on long-tail keywords with high commercial intent. Here's your optimized strategy...",
  "Excellent idea! For this email sequence, I suggest a 5-touch nurture campaign. Subject line A/B tests show 'Unlock your' performs better. Here's the flow...",
  "Strategic thinking! For this campaign, let's segment your audience into three buckets: Awareness, Consideration, and Decision. Here's the content matrix...",
];

const brandVoices = [
  "Professional + Friendly",
  "Bold + Energetic",
  "Luxury + Sophisticated",
  "Casual + Witty",
];

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
    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as HTMLElement;
      if (
        target.closest(".chat-menu") ||
        target.closest(".chat-menu-button")
      ) {
        return;
      }
      setChatMenuOpenId(null);
    };

    document.addEventListener("pointerdown", handlePointerDown);
    return () =>
      document.removeEventListener("pointerdown", handlePointerDown);
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
    startConversation(
      `Loaded chat: ${chat.title}. How can I help you next?`
    );
  };

  const handleChatAction = (
    action: "use" | "rename" | "delete" | "star",
    chatId: string
  ) => {
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
          item.id === chatId
            ? { ...item, title: nextTitle.trim() }
            : item
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

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
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
    <div className="marketing-ai">
      <div
        className={`overlay ${sidebarOpen ? "active" : ""}`}
        onClick={() => setSidebarOpen(false)}
      />

      <aside className={`sidebar ${sidebarOpen ? "open" : "closed"}`}>
        <div className="brand">
          <div className="brand-icon">
            <Rocket className="icon" aria-hidden="true" />
          </div>
          <div className="brand-text">Marketing AI</div>
        </div>

        <nav className="nav-section">
          <div className="chat-section">
            <button
              type="button"
              className="chat-dropdown-toggle"
              onClick={() => setChatsOpen((prev) => !prev)}
              aria-expanded={chatsOpen}
            >
              <span>Chats</span>
              <ChevronDown
                className={`icon ${chatsOpen ? "open" : ""}`}
                aria-hidden="true"
              />
            </button>
            {chatsOpen && (
              <div className="chat-list">
                {chatItems.map((chat) => (
                  <div
                    key={chat.id}
                    className={`chat-item ${
                      activeChatId === chat.id ? "active" : ""
                    }`}
                  >
                    <button
                      type="button"
                      className="chat-main"
                      onClick={() => handleChatSelect(chat.id)}
                    >
                      <div className="chat-title">
                        <span>{chat.title}</span>
                        {chat.starred && (
                          <Star className="chat-star" aria-hidden="true" />
                        )}
                      </div>
                      <div className="chat-meta">
                        <span className={`status-dot ${chat.statusClass}`} />
                        <span>{chat.meta}</span>
                      </div>
                    </button>
                    <div className="chat-actions">
                      <button
                        type="button"
                        className="chat-menu-button"
                        onClick={(event) => {
                          event.stopPropagation();
                          setChatMenuOpenId((prev) =>
                            prev === chat.id ? null : chat.id
                          );
                        }}
                        aria-expanded={chatMenuOpenId === chat.id}
                        aria-haspopup="menu"
                        aria-label="Chat options"
                      >
                        <MoreHorizontal className="icon" aria-hidden="true" />
                      </button>
                      {chatMenuOpenId === chat.id && (
                        <div className="chat-menu" role="menu">
                          <button
                            type="button"
                            className="chat-menu-item"
                            role="menuitem"
                            onClick={(event) => {
                              event.stopPropagation();
                              handleChatAction("use", chat.id);
                            }}
                          >
                            <MessageSquare className="icon" aria-hidden="true" />
                            <span>Use</span>
                          </button>
                          <button
                            type="button"
                            className="chat-menu-item"
                            role="menuitem"
                            onClick={(event) => {
                              event.stopPropagation();
                              handleChatAction("rename", chat.id);
                            }}
                          >
                            <PencilLine className="icon" aria-hidden="true" />
                            <span>Rename</span>
                          </button>
                          <button
                            type="button"
                            className="chat-menu-item"
                            role="menuitem"
                            onClick={(event) => {
                              event.stopPropagation();
                              handleChatAction("star", chat.id);
                            }}
                          >
                            <Star className="icon" aria-hidden="true" />
                            <span>{chat.starred ? "Unstar" : "Star"}</span>
                          </button>
                          <button
                            type="button"
                            className="chat-menu-item danger"
                            role="menuitem"
                            onClick={(event) => {
                              event.stopPropagation();
                              handleChatAction("delete", chat.id);
                            }}
                          >
                            <Trash2 className="icon" aria-hidden="true" />
                            <span>Delete</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="nav-header">Tools</div>
          <ul className="nav-list">
            {tools.map((tool) => {
              const Icon = tool.icon;
              return (
                <li key={tool.id}>
                  <button
                    type="button"
                    className={`nav-item ${
                      activeTool === tool.id ? "active" : ""
                    }`}
                    onClick={() => handleToolClick(tool.id)}
                  >
                    <span className="nav-icon">
                      <Icon className="icon" aria-hidden="true" />
                    </span>
                    <span>{tool.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="nav-header">Library</div>
          <ul className="nav-list">
            {library.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className={`nav-item ${
                      activeTool === item.id ? "active" : ""
                    }`}
                    onClick={() => handleToolClick(item.id)}
                  >
                    <span className="nav-icon">
                      <Icon className="icon" aria-hidden="true" />
                    </span>
                    <span>{item.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="sidebar-footer">
          <button type="button" className="user-profile">
            <div className="avatar">JD</div>
            <div className="user-info">
              <div className="user-name">John Doe</div>
              <div className="user-role">Marketing Manager</div>
            </div>
            <Settings className="icon" aria-hidden="true" />
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="header">
          <div className="header-left">
            <button
              className="menu-toggle"
              type="button"
              onClick={() => setSidebarOpen((prev) => !prev)}
              aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
            >
              {sidebarOpen ? (
                <X className="icon" aria-hidden="true" />
              ) : (
                <Menu className="icon" aria-hidden="true" />
              )}
            </button>
            <div className="page-title">
              <PageIcon className="icon" aria-hidden="true" />
              <span>{pageTitle}</span>
            </div>
          </div>
          <div className="header-brand">
            <Sparkles className="icon" aria-hidden="true" />
            <span>AI Assistant</span>
          </div>
          <div className="header-actions">
            <button className="icon-button" type="button" title="History">
              <Clock className="icon" aria-hidden="true" />
            </button>
            <button className="icon-button" type="button" title="Share">
              <Share2 className="icon" aria-hidden="true" />
            </button>
            <button className="icon-button" type="button" title="Settings">
              <Settings className="icon" aria-hidden="true" />
            </button>
          </div>
        </header>

        <div className="chat-wrapper" ref={chatWrapperRef}>
          {!hasMessages && (
            <div className="empty-state">
              <div className="empty-icon">
                <Target className="icon" aria-hidden="true" />
              </div>
              <h1 className="empty-title">Ready to boost your marketing?</h1>
              <p className="empty-subtitle">
                I'm your digital marketing assistant. I can help with content
                creation, SEO optimization, campaign strategy, and more.
              </p>

              <div className="quick-actions">
                {quickActions.map((action) => {
                  const Icon = action.icon;
                  return (
                    <button
                      key={action.title}
                      type="button"
                      className="action-card"
                      onClick={() => handleQuickAction(action.prompt)}
                    >
                      <div className="action-icon">
                        <Icon className="icon" aria-hidden="true" />
                      </div>
                      <div className="action-title">{action.title}</div>
                      <div className="action-desc">{action.description}</div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {hasMessages && (
            <div className="messages-container">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`message ${message.sender}`}
                >
                  <div className="message-avatar">
                    {message.sender === "bot" ? (
                      <Rocket className="icon" aria-hidden="true" />
                    ) : (
                      <User className="icon" aria-hidden="true" />
                    )}
                  </div>
                  <div className="message-body">
                    <div className="message-content">{message.text}</div>
                    <div className="message-time">{message.time}</div>
                  </div>
                </div>
              ))}

              {isTyping && (
                <div className="message bot">
                  <div className="message-avatar">
                    <Rocket className="icon" aria-hidden="true" />
                  </div>
                  <div className="message-body">
                    <div className="message-content">
                      <div className="typing">
                        <div className="typing-dot" />
                        <div className="typing-dot" />
                        <div className="typing-dot" />
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="input-section">
          <div className="input-container">
            <div className="input-wrapper">
              <textarea
                ref={textareaRef}
                className="message-input"
                placeholder="Ask me to write ad copy, optimize SEO, or plan a campaign..."
                rows={1}
                value={messageInput}
                onChange={(event) => handleInputChange(event.target.value)}
                onKeyDown={handleKeyDown}
              />
              <div className="input-toolbar">
                <button className="tool-btn" type="button" title="Attach">
                  <Paperclip className="icon" aria-hidden="true" />
                </button>
                <button className="tool-btn" type="button" title="Voice">
                  <Mic className="icon" aria-hidden="true" />
                </button>
                <button className="send-button" type="button" onClick={() => handleSend()}>
                  <SendHorizontal className="icon" aria-hidden="true" />
                </button>
              </div>
            </div>
            <div className="input-footer">
              <span>Marketing AI can make mistakes. Verify important data.</span>
              <button
                type="button"
                className="brand-voice-badge"
                onClick={toggleBrandVoice}
              >
                <span className="badge-dot" aria-hidden="true" />
                <span>{brandVoices[brandVoiceIndex]}</span>
                <span className="badge-caret" aria-hidden="true">
                  v
                </span>
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
