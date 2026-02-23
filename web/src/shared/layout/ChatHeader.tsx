"use client";

import type { LucideIcon } from "lucide-react";
import { Clock, Share2 } from "lucide-react";
import { usePathname } from "next/navigation";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/ui/select";
import { useModelCards } from "./ModelCardsContext";

const iconClass = "size-[18px]";
const iconButtonBase =
  "h-8 w-8 rounded-md border border-marketing-border bg-transparent text-marketing-text-secondary hover:bg-marketing-surface hover:text-marketing-text-primary hover:border-input";

type ChatHeaderProps = {
  pageTitle: string;
  PageIcon: LucideIcon;
};

export function ChatHeader({ pageTitle, PageIcon }: ChatHeaderProps) {
  const pathname = usePathname();
  const isChatRoute = pathname === "/" || /^\/c\/[^/]+$/.test(pathname);
  const { items, selectedModelId, isLoading, setActiveModel } = useModelCards();

  return (
    <header className="sticky top-0 z-50 flex h-[60px] items-center justify-between border-b border-marketing-border bg-marketing-surface-translucent px-4 backdrop-blur-[12px] md:px-6">
      <div className="flex items-center gap-3">
        {isChatRoute ? (
          <Select
            value={selectedModelId ?? undefined}
            onValueChange={(value) => {
              void setActiveModel(value);
            }}
            disabled={isLoading || items.length === 0}
          >
            <SelectTrigger className="h-8 min-w-[220px] border-marketing-border bg-marketing-surface text-sm">
              <SelectValue
                placeholder={isLoading ? "Loading models..." : "Select model"}
              />
            </SelectTrigger>
            <SelectContent>
              {items.map((item) => (
                <SelectItem key={item.id} value={item.id}>
                  {item.display_name} ({item.model_name})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : null}
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
