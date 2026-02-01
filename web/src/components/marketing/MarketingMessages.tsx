import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Rocket, User } from "lucide-react";
import type { Message } from "./types";

const iconClass = "size-[18px]";
const gradientClass =
  "bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to";

const bubbleBaseClass =
  "rounded-2xl border border-marketing-border bg-marketing-surface text-marketing-text-primary shadow-marketing-subtle";

const bubbleContentClass = "px-5 py-4 leading-relaxed whitespace-pre-line";

type MarketingMessagesProps = {
  messages: Message[];
  isTyping: boolean;
};

export function MarketingMessages({ messages, isTyping }: MarketingMessagesProps) {
  return (
    <div className="mx-auto flex w-full max-w-[900px] flex-col gap-6">
      {messages.map((message) => (
        <div
          key={message.id}
          className={cn(
            "flex gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300",
            message.sender === "user" && "flex-row-reverse"
          )}
        >
          <div
            className={cn(
              "flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full text-marketing-on-primary shadow-marketing-soft",
              message.sender === "bot"
                ? gradientClass
                : "bg-marketing-text-primary"
            )}
          >
            {message.sender === "bot" ? (
              <Rocket className={iconClass} aria-hidden="true" />
            ) : (
              <User className={iconClass} aria-hidden="true" />
            )}
          </div>
          <div className="flex max-w-[80%] flex-col gap-1.5">
            <Card
              className={cn(
                "gap-0 py-0",
                bubbleBaseClass,
                message.sender === "user"
                  ? "border-0 bg-marketing-text-primary text-marketing-on-primary rounded-br-[4px]"
                  : "rounded-bl-[4px]"
              )}
            >
              <CardContent className={bubbleContentClass}>
                {message.text}
              </CardContent>
            </Card>
            <div className="px-1 text-xs text-marketing-text-muted">
              {message.time}
            </div>
          </div>
        </div>
      ))}

      {isTyping && (
        <div className="flex gap-4">
          <div
            className={cn(
              "flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full text-marketing-on-primary shadow-marketing-soft",
              gradientClass
            )}
          >
            <Rocket className={iconClass} aria-hidden="true" />
          </div>
          <div className="flex max-w-[80%] flex-col gap-1.5">
            <Card
              className={cn(
                "gap-0 py-0 rounded-2xl rounded-bl-[4px]",
                bubbleBaseClass
              )}
            >
              <CardContent className={bubbleContentClass}>
                <div className="flex gap-1 px-4 py-3">
                  <div className="h-2 w-2 animate-bounce rounded-full bg-marketing-primary" />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-marketing-primary [animation-delay:0.2s]" />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-marketing-primary [animation-delay:0.4s]" />
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
