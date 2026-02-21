import type { ComponentPropsWithoutRef } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import { cn } from "@/shared/lib/utils";

type AssistantMarkdownProps = {
  content: string;
};

function Paragraph({ className, ...props }: ComponentPropsWithoutRef<"p">) {
  return <p className={cn("my-0 leading-relaxed", className)} {...props} />;
}

function Heading1({ className, ...props }: ComponentPropsWithoutRef<"h1">) {
  return (
    <h1
      className={cn(
        "mt-5 mb-2 text-lg font-semibold leading-tight text-marketing-text-primary",
        className,
      )}
      {...props}
    />
  );
}

function Heading2({ className, ...props }: ComponentPropsWithoutRef<"h2">) {
  return (
    <h2
      className={cn(
        "mt-4 mb-2 text-base font-semibold leading-tight text-marketing-text-primary",
        className,
      )}
      {...props}
    />
  );
}

function Heading3({ className, ...props }: ComponentPropsWithoutRef<"h3">) {
  return (
    <h3
      className={cn(
        "mt-4 mb-2 text-[0.95rem] font-semibold leading-tight text-marketing-text-primary",
        className,
      )}
      {...props}
    />
  );
}

function Heading4({ className, ...props }: ComponentPropsWithoutRef<"h4">) {
  return (
    <h4
      className={cn(
        "mt-3 mb-2 text-[0.9rem] font-semibold leading-tight text-marketing-text-primary",
        className,
      )}
      {...props}
    />
  );
}

function UnorderedList({
  className,
  ...props
}: ComponentPropsWithoutRef<"ul">) {
  return (
    <ul
      className={cn(
        "my-2 ml-5 list-disc space-y-1 text-marketing-text-primary",
        className,
      )}
      {...props}
    />
  );
}

function OrderedList({ className, ...props }: ComponentPropsWithoutRef<"ol">) {
  return (
    <ol
      className={cn(
        "my-2 ml-5 list-decimal space-y-1 text-marketing-text-primary",
        className,
      )}
      {...props}
    />
  );
}

function ListItem({ className, ...props }: ComponentPropsWithoutRef<"li">) {
  return <li className={cn("pl-1", className)} {...props} />;
}

function Blockquote({
  className,
  ...props
}: ComponentPropsWithoutRef<"blockquote">) {
  return (
    <blockquote
      className={cn(
        "my-2 border-l-2 border-marketing-border pl-3 text-marketing-text-secondary italic",
        className,
      )}
      {...props}
    />
  );
}

function InlineCode({ className, ...props }: ComponentPropsWithoutRef<"code">) {
  return (
    <code
      className={cn(
        "rounded-[4px] bg-marketing-accent-medium px-1 py-0.5 font-mono text-[0.84em] text-marketing-text-primary",
        className,
      )}
      {...props}
    />
  );
}

function CodeBlock({ className, ...props }: ComponentPropsWithoutRef<"pre">) {
  return (
    <pre
      className={cn(
        "my-2 overflow-x-auto rounded-lg border border-marketing-border bg-marketing-surface-translucent p-3 font-mono text-xs leading-5 text-marketing-text-primary [&_code]:bg-transparent [&_code]:p-0",
        className,
      )}
      {...props}
    />
  );
}

function Link({ className, ...props }: ComponentPropsWithoutRef<"a">) {
  return (
    <a
      {...props}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "text-marketing-primary underline decoration-marketing-primary/50 underline-offset-2 transition-colors hover:text-marketing-secondary",
        className,
      )}
    />
  );
}

function HorizontalRule({
  className,
  ...props
}: ComponentPropsWithoutRef<"hr">) {
  return (
    <hr className={cn("my-3 border-marketing-border", className)} {...props} />
  );
}

const markdownComponents: Components = {
  p: Paragraph,
  h1: Heading1,
  h2: Heading2,
  h3: Heading3,
  h4: Heading4,
  ul: UnorderedList,
  ol: OrderedList,
  li: ListItem,
  blockquote: Blockquote,
  code: InlineCode,
  pre: CodeBlock,
  a: Link,
  hr: HorizontalRule,
};

export function AssistantMarkdown({ content }: AssistantMarkdownProps) {
  return (
    <div className="space-y-3 break-words">
      <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>
    </div>
  );
}
