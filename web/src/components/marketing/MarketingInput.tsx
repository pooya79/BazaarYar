import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { Mic, Paperclip, SendHorizontal } from "lucide-react";
import type { KeyboardEvent, RefObject } from "react";

const iconClass = "size-[18px]";
const gradientClass =
  "bg-gradient-to-br from-[var(--marketing-gradient-from)] to-[var(--marketing-gradient-to)]";

type MarketingInputProps = {
  textareaRef: RefObject<HTMLTextAreaElement>;
  value: string;
  onChange: (value: string) => void;
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
  onSend: () => void;
  brandVoice: string;
  onToggleBrandVoice: () => void;
};

export function MarketingInput({
  textareaRef,
  value,
  onChange,
  onKeyDown,
  onSend,
  brandVoice,
  onToggleBrandVoice,
}: MarketingInputProps) {
  return (
    <div className="border-t border-[var(--marketing-border)] bg-[var(--marketing-surface-translucent)] p-4 backdrop-blur-[12px] md:px-8 md:py-6">
      <div className="mx-auto max-w-[900px]">
        <div
          className={cn(
            "flex items-end gap-3 rounded-2xl border-2 border-[var(--marketing-border)] bg-[var(--marketing-surface)] py-2 pr-2 pl-5 transition-all duration-300",
            "shadow-[var(--marketing-shadow-soft)]",
            "focus-within:border-[var(--marketing-secondary)] focus-within:ring-4 focus-within:ring-[var(--marketing-accent-glow)]"
          )}
        >
          <Textarea
            ref={textareaRef}
            className="min-h-0 max-h-[150px] flex-1 resize-none border-0 bg-transparent px-0 py-3 text-base text-[var(--marketing-text-primary)] placeholder:text-[var(--marketing-text-muted)] shadow-none focus-visible:ring-0"
            placeholder="Ask me to write ad copy, optimize SEO, or plan a campaign..."
            rows={1}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={onKeyDown}
          />
          <div className="flex gap-2 pb-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 rounded-lg text-[var(--marketing-text-muted)] hover:bg-[var(--marketing-accent-medium)] hover:text-[var(--marketing-primary)]"
              type="button"
              title="Attach"
            >
              <Paperclip className={iconClass} aria-hidden="true" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 rounded-lg text-[var(--marketing-text-muted)] hover:bg-[var(--marketing-accent-medium)] hover:text-[var(--marketing-primary)]"
              type="button"
              title="Voice"
            >
              <Mic className={iconClass} aria-hidden="true" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className={cn(
                "h-10 w-10 rounded-xl text-[var(--marketing-on-primary)] transition-all duration-200 hover:text-[var(--marketing-on-primary)]",
                gradientClass,
                "shadow-[var(--marketing-shadow-soft)]",
                "hover:scale-105 hover:-rotate-6 hover:shadow-[var(--marketing-shadow-hover)]"
              )}
              type="button"
              onClick={onSend}
            >
              <SendHorizontal className={iconClass} aria-hidden="true" />
            </Button>
          </div>
        </div>
        <div className="mt-3 flex flex-col items-start gap-3 px-2 text-xs text-[var(--marketing-text-muted)] md:flex-row md:items-center md:justify-between">
          <span>Marketing AI can make mistakes. Verify important data.</span>
          <Button
            type="button"
            variant="ghost"
            className="h-auto rounded-full border-0 bg-[var(--marketing-accent-medium)] px-2.5 py-1 text-xs font-semibold text-[var(--marketing-primary)] hover:bg-[var(--marketing-accent-strong)] hover:text-[var(--marketing-primary)]"
            onClick={onToggleBrandVoice}
          >
            <span
              className="h-2 w-2 rounded-full bg-[var(--marketing-primary)]"
              aria-hidden="true"
            />
            <span>{brandVoice}</span>
            <span className="text-xs leading-none" aria-hidden="true">
              v
            </span>
          </Button>
        </div>
      </div>
    </div>
  );
}
