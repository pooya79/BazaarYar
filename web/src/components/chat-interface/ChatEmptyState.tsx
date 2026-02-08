import { Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { QuickAction } from "./types";

const iconXlClass = "size-6";

type ChatEmptyStateProps = {
  actions: QuickAction[];
  onAction: (prompt: string) => void;
};

export function ChatEmptyState({ actions, onAction }: ChatEmptyStateProps) {
  return (
    <div className="mx-auto max-w-[800px] pt-12 text-center md:pt-20">
      <div className="mb-6 inline-flex h-12 w-12 items-center justify-center rounded-xl border border-marketing-border bg-secondary text-marketing-primary shadow-marketing-subtle">
        <Target className={iconXlClass} aria-hidden="true" />
      </div>
      <h1 className="mb-2 text-[1.5rem] font-bold tracking-[-0.02em] text-marketing-text-primary">
        Ready to boost your marketing?
      </h1>
      <p className="mx-auto mb-12 max-w-[42rem] text-base leading-relaxed text-marketing-text-secondary">
        I'm your digital marketing assistant. I can help with content creation,
        SEO optimization, campaign strategy, and more.
      </p>

      <div className="mx-auto grid max-w-[800px] grid-cols-1 gap-3 text-left md:grid-cols-2">
        {actions.map((action) => {
          const Icon = action.icon;
          return (
            <Button
              key={action.title}
              type="button"
              variant="ghost"
              className={cn(
                "h-auto w-full flex-col items-start gap-1 rounded-lg border border-marketing-border bg-marketing-surface px-4 py-4 text-left text-marketing-text-primary shadow-marketing-subtle transition-all duration-200",
                "hover:-translate-y-0.5 hover:border-marketing-primary hover:bg-marketing-surface hover:text-marketing-text-primary hover:shadow-marketing-hover",
              )}
              onClick={() => onAction(action.prompt)}
            >
              <div className="mb-1 inline-flex items-center gap-2">
                <span className="inline-flex h-5 w-5 items-center justify-center text-marketing-primary">
                  <Icon className="size-5" aria-hidden="true" />
                </span>
                <div className="text-[0.875rem] font-semibold">
                  {action.title}
                </div>
              </div>
              <div className="pl-7 text-[0.8rem] leading-snug text-marketing-text-secondary">
                {action.description}
              </div>
            </Button>
          );
        })}
      </div>
    </div>
  );
}
