import { Target } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { QuickAction } from "./types";

const iconLargeClass = "size-6";
const iconXlClass = "size-14";

type ChatEmptyStateProps = {
  actions: QuickAction[];
  onAction: (prompt: string) => void;
};

export function ChatEmptyState({
  actions,
  onAction,
}: ChatEmptyStateProps) {
  return (
    <div className="mx-auto max-w-[800px] pt-[60px] text-center">
      <div className="mb-6 inline-flex h-14 w-14 items-center justify-center text-marketing-primary motion-safe:animate-bounce">
        <Target className={iconXlClass} aria-hidden="true" />
      </div>
      <h1 className="mb-3 text-[2rem] font-bold text-marketing-text-primary">
        Ready to get started?
      </h1>
      <p className="mb-10 text-[1.1rem] leading-relaxed text-marketing-text-secondary">
        I'm your digital assistant. I can help with content creation, SEO
        optimization, campaign strategy, and more.
      </p>

      <div className="mx-auto grid max-w-[800px] grid-cols-1 gap-4 md:grid-cols-[repeat(auto-fit,minmax(240px,1fr))]">
        {actions.map((action) => {
          const Icon = action.icon;
          return (
            <Button
              key={action.title}
              type="button"
              variant="ghost"
              className={cn(
                "h-auto w-full flex-col items-start gap-2 rounded-xl border border-marketing-border bg-marketing-surface p-5 text-left text-marketing-text-primary transition-all duration-300",
                "hover:-translate-y-1 hover:border-marketing-secondary hover:bg-marketing-surface hover:text-marketing-text-primary hover:shadow-marketing-hover",
              )}
              onClick={() => onAction(action.prompt)}
            >
              <div className="mb-1 inline-flex">
                <Icon className={iconLargeClass} aria-hidden="true" />
              </div>
              <div className="text-[0.95rem] font-semibold">{action.title}</div>
              <div className="text-[0.85rem] leading-snug text-marketing-text-muted">
                {action.description}
              </div>
            </Button>
          );
        })}
      </div>
    </div>
  );
}
