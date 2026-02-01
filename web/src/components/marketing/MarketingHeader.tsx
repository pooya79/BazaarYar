import type { LucideIcon } from "lucide-react";
import { Clock, Menu, Settings, Share2, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const iconClass = "size-[18px]";
const iconMenuClass = "size-[22px]";
const iconButtonBase =
  "rounded-[10px] text-marketing-text-secondary border-marketing-border bg-marketing-surface hover:bg-marketing-surface hover:-translate-y-0.5 hover:border-marketing-primary hover:text-marketing-primary";

type MarketingHeaderProps = {
  pageTitle: string;
  PageIcon: LucideIcon;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
};

export function MarketingHeader({
  pageTitle,
  PageIcon,
  sidebarOpen,
  onToggleSidebar,
}: MarketingHeaderProps) {
  return (
    <header className="sticky top-0 z-50 grid h-[70px] grid-cols-[auto_1fr_auto] items-center border-b border-marketing-border bg-marketing-surface-translucent px-4 backdrop-blur-[12px] md:px-8">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          className="rounded-lg text-marketing-text-primary hover:bg-marketing-accent-medium hover:text-marketing-text-primary"
          type="button"
          onClick={onToggleSidebar}
          aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
        >
          {sidebarOpen ? (
            <X className={iconMenuClass} aria-hidden="true" />
          ) : (
            <Menu className={iconMenuClass} aria-hidden="true" />
          )}
        </Button>
        <div className="flex items-center gap-2 text-xl font-bold text-marketing-text-primary">
          <PageIcon className={iconClass} aria-hidden="true" />
          <span>{pageTitle}</span>
        </div>
      </div>
      <div className="inline-flex items-center justify-self-center gap-2 text-base font-bold text-marketing-text-primary">
        <Sparkles
          className={cn(iconClass, "text-marketing-primary")}
          aria-hidden="true"
        />
        <span>AI Assistant</span>
      </div>
      <div className="flex gap-3">
        <Button
          variant="outline"
          size="icon"
          className={cn(
            iconButtonBase,
            "shadow-none hover:shadow-marketing-soft",
          )}
          type="button"
          title="History"
        >
          <Clock className={iconClass} aria-hidden="true" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          className={cn(
            iconButtonBase,
            "shadow-none hover:shadow-marketing-soft",
          )}
          type="button"
          title="Share"
        >
          <Share2 className={iconClass} aria-hidden="true" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          className={cn(
            iconButtonBase,
            "shadow-none hover:shadow-marketing-soft",
          )}
          type="button"
          title="Settings"
        >
          <Settings className={iconClass} aria-hidden="true" />
        </Button>
      </div>
    </header>
  );
}
