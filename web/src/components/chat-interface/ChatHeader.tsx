import type { LucideIcon } from "lucide-react";
import { Clock, Menu, Share2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const iconClass = "size-[18px]";
const iconMenuClass = "size-[20px]";
const iconButtonBase =
  "h-8 w-8 rounded-md border border-marketing-border bg-transparent text-marketing-text-secondary hover:bg-marketing-surface hover:text-marketing-text-primary hover:border-input";

type ChatHeaderProps = {
  pageTitle: string;
  PageIcon: LucideIcon;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
};

export function ChatHeader({
  pageTitle,
  PageIcon,
  sidebarOpen,
  onToggleSidebar,
}: ChatHeaderProps) {
  return (
    <header className="sticky top-0 z-50 flex h-[60px] items-center justify-between border-b border-marketing-border bg-marketing-surface-translucent px-4 backdrop-blur-[12px] md:px-6">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="rounded-md text-marketing-text-secondary hover:bg-marketing-accent-medium hover:text-marketing-text-primary md:hidden"
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
        <div className="flex items-center gap-2 text-base font-semibold text-marketing-text-primary">
          <PageIcon
            className={cn(iconClass, "text-marketing-primary")}
            aria-hidden="true"
          />
          <span>{pageTitle}</span>
        </div>
      </div>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="icon"
          className={iconButtonBase}
          type="button"
          title="History"
        >
          <Clock className={iconClass} aria-hidden="true" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          className={iconButtonBase}
          type="button"
          title="Share"
        >
          <Share2 className={iconClass} aria-hidden="true" />
        </Button>
      </div>
    </header>
  );
}
