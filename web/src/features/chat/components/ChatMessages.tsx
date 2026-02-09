"use client";

import { Bot, User } from "lucide-react";
import { useMemo, useState } from "react";
import type {
  AssistantTurn,
  ChatTimelineItem,
} from "@/features/chat/model/types";
import { cn } from "@/shared/lib/utils";
import { Card, CardContent } from "@/shared/ui/card";
import { AssistantMessageCard } from "./AssistantMessageCard";
import { MessageAttachments } from "./MessageAttachments";
import { ToolCallDetailsSheet } from "./ToolCallDetailsSheet";

const iconClass = "size-[18px]";

const bubbleBaseClass =
  "rounded-xl border border-marketing-border bg-marketing-surface text-marketing-text-primary shadow-marketing-subtle";

const bubbleContentClass =
  "px-4 py-3.5 leading-relaxed whitespace-pre-line text-[0.9375rem]";

type ChatMessagesProps = {
  timeline: ChatTimelineItem[];
  isTyping: boolean;
};

type SelectedTool = {
  turnId: string;
  toolKey: string;
};

function findAssistantTurn(
  timeline: ChatTimelineItem[],
  turnId: string,
): AssistantTurn | null {
  for (const item of timeline) {
    if (item.sender === "assistant" && item.id === turnId) {
      return item;
    }
  }
  return null;
}

export function ChatMessages({ timeline, isTyping }: ChatMessagesProps) {
  const [selectedTool, setSelectedTool] = useState<SelectedTool | null>(null);

  const selectedTurn = useMemo(() => {
    if (!selectedTool) {
      return null;
    }
    return findAssistantTurn(timeline, selectedTool.turnId);
  }, [timeline, selectedTool]);

  const selectedCall = useMemo(() => {
    if (!selectedTurn || !selectedTool) {
      return null;
    }
    return (
      selectedTurn.toolCalls.find(
        (tool) => tool.key === selectedTool.toolKey,
      ) || null
    );
  }, [selectedTool, selectedTurn]);

  return (
    <>
      <div className="mx-auto flex w-full max-w-[800px] flex-col gap-8">
        {timeline.map((item) => (
          <div
            key={item.id}
            className={cn(
              "animate-in fade-in slide-in-from-bottom-2 flex gap-4 duration-300",
              item.sender === "user" && "flex-row-reverse",
            )}
          >
            <div
              className={cn(
                "flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border text-[0.75rem] font-semibold shadow-none",
                item.sender === "assistant"
                  ? "border-transparent bg-marketing-primary text-marketing-on-primary"
                  : "border-marketing-border bg-secondary text-marketing-text-secondary",
              )}
            >
              {item.sender === "assistant" ? (
                <Bot className={iconClass} aria-hidden="true" />
              ) : (
                <User className={iconClass} aria-hidden="true" />
              )}
            </div>

            {item.sender === "assistant" ? (
              <div className="flex w-full max-w-[70%] flex-col gap-1">
                <AssistantMessageCard
                  turn={item}
                  onToolSelect={(toolKey) =>
                    setSelectedTool({ turnId: item.id, toolKey })
                  }
                />
              </div>
            ) : (
              <div className="flex max-w-[70%] flex-col gap-1">
                <Card
                  className={cn(
                    "gap-0 rounded-xl rounded-br-[4px] border-0 bg-marketing-text-primary py-0 text-marketing-on-primary",
                    bubbleBaseClass,
                  )}
                >
                  <CardContent className={bubbleContentClass}>
                    <div className="space-y-3">
                      {item.text ? <div>{item.text}</div> : null}
                      {item.attachments ? (
                        <MessageAttachments attachments={item.attachments} />
                      ) : null}
                    </div>
                  </CardContent>
                </Card>
                <div className="px-1 text-[0.7rem] text-marketing-text-muted">
                  {item.time}
                </div>
              </div>
            )}
          </div>
        ))}

        {isTyping ? (
          <div className="flex gap-4">
            <div
              className={cn(
                "flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-marketing-primary text-marketing-on-primary",
              )}
            >
              <Bot className={iconClass} aria-hidden="true" />
            </div>
            <div className="flex max-w-[70%] flex-col gap-1">
              <Card
                className={cn(
                  "gap-0 rounded-xl rounded-bl-[4px] py-0",
                  bubbleBaseClass,
                )}
              >
                <CardContent className={bubbleContentClass}>
                  <div className="flex gap-1 px-2 py-1">
                    <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-marketing-primary" />
                    <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-marketing-primary [animation-delay:0.2s]" />
                    <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-marketing-primary [animation-delay:0.4s]" />
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        ) : null}
      </div>

      <ToolCallDetailsSheet
        open={Boolean(selectedTool && selectedCall && selectedTurn)}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedTool(null);
          }
        }}
        toolCall={selectedCall}
        turnTime={selectedTurn?.time || ""}
      />
    </>
  );
}
