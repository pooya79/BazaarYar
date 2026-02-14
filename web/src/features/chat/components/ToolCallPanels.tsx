"use client";

import { Copy } from "lucide-react";
import { Button } from "@/shared/ui/button";

type MetadataItem = {
  label: string;
  value: string | null | undefined;
};

type PythonCodePanelProps = {
  title: string;
  code: string | null;
  emptyLabel: string;
};

type OutputPanelProps = {
  title: string;
  output: string | null | undefined;
  emptyLabel: string;
};

type MetadataPanelProps = {
  title: string;
  items: MetadataItem[];
  emptyLabel: string;
};

const PYTHON_KEYWORDS = new Set([
  "and",
  "as",
  "assert",
  "async",
  "await",
  "break",
  "class",
  "continue",
  "def",
  "del",
  "elif",
  "else",
  "except",
  "False",
  "finally",
  "for",
  "from",
  "global",
  "if",
  "import",
  "in",
  "is",
  "lambda",
  "None",
  "nonlocal",
  "not",
  "or",
  "pass",
  "raise",
  "return",
  "True",
  "try",
  "while",
  "with",
  "yield",
]);

function copyText(text: string) {
  if (!text.trim()) {
    return;
  }
  void navigator.clipboard?.writeText(text).catch(() => undefined);
}

function PanelHeader({
  title,
  copyValue,
}: {
  title: string;
  copyValue?: string | null;
}) {
  return (
    <div className="mb-2 flex items-center justify-between gap-2">
      <h4 className="text-[0.7rem] font-semibold uppercase tracking-[0.08em] text-marketing-text-muted">
        {title}
      </h4>
      {copyValue ? (
        <Button
          type="button"
          variant="ghost"
          size="xs"
          className="h-6 border border-marketing-border bg-marketing-surface-translucent px-2 text-[0.65rem] text-marketing-text-muted hover:text-marketing-text-primary"
          onClick={() => copyText(copyValue)}
        >
          <Copy className="size-3" aria-hidden="true" />
          Copy
        </Button>
      ) : null}
    </div>
  );
}

type TokenKind = "plain" | "keyword" | "string" | "comment" | "number";

function pushToken(
  tokens: Array<{ text: string; kind: TokenKind }>,
  text: string,
  kind: TokenKind,
) {
  if (!text) {
    return;
  }
  tokens.push({ text, kind });
}

function tokenizePythonLine(line: string) {
  const tokens: Array<{ text: string; kind: TokenKind }> = [];
  let cursor = 0;

  while (cursor < line.length) {
    const char = line[cursor];

    if (char === "#") {
      pushToken(tokens, line.slice(cursor), "comment");
      break;
    }

    if (char === "'" || char === '"') {
      const quote = char;
      let end = cursor + 1;
      let escaped = false;
      while (end < line.length) {
        const current = line[end];
        if (!escaped && current === quote) {
          end += 1;
          break;
        }
        escaped = !escaped && current === "\\";
        if (current !== "\\") {
          escaped = false;
        }
        end += 1;
      }
      pushToken(tokens, line.slice(cursor, end), "string");
      cursor = end;
      continue;
    }

    if (/[A-Za-z_]/.test(char)) {
      let end = cursor + 1;
      while (end < line.length && /[A-Za-z0-9_]/.test(line[end] ?? "")) {
        end += 1;
      }
      const word = line.slice(cursor, end);
      pushToken(tokens, word, PYTHON_KEYWORDS.has(word) ? "keyword" : "plain");
      cursor = end;
      continue;
    }

    if (/[0-9]/.test(char)) {
      let end = cursor + 1;
      while (end < line.length && /[0-9._]/.test(line[end] ?? "")) {
        end += 1;
      }
      pushToken(tokens, line.slice(cursor, end), "number");
      cursor = end;
      continue;
    }

    pushToken(tokens, char, "plain");
    cursor += 1;
  }

  return tokens;
}

function tokenClass(kind: TokenKind) {
  if (kind === "keyword") {
    return "text-marketing-primary";
  }
  if (kind === "string") {
    return "text-marketing-text-secondary";
  }
  if (kind === "comment") {
    return "text-marketing-text-muted";
  }
  if (kind === "number") {
    return "text-marketing-text-secondary";
  }
  return "text-marketing-text-primary";
}

export function PythonCodePanel({
  title,
  code,
  emptyLabel,
}: PythonCodePanelProps) {
  const lines = code ? code.split(/\r?\n/) : [];

  return (
    <section>
      <PanelHeader title={title} copyValue={code} />
      {code ? (
        <div className="overflow-x-auto rounded-lg border border-marketing-border bg-marketing-surface-translucent">
          <pre className="min-w-max p-3 text-xs leading-5">
            {lines.map((line, index) => (
              <div key={`${index}-${line}`} className="flex">
                <span className="mr-3 w-8 select-none text-right text-marketing-text-muted">
                  {index + 1}
                </span>
                <code className="whitespace-pre">
                  {line
                    ? tokenizePythonLine(line).map((token, tokenIndex) => (
                        <span
                          key={`${index}-${tokenIndex}-${token.text}`}
                          className={tokenClass(token.kind)}
                        >
                          {token.text}
                        </span>
                      ))
                    : " "}
                </code>
              </div>
            ))}
          </pre>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-marketing-border bg-marketing-surface-translucent p-3 text-xs text-marketing-text-muted">
          {emptyLabel}
        </div>
      )}
    </section>
  );
}

export function OutputPanel({ title, output, emptyLabel }: OutputPanelProps) {
  return (
    <section>
      <PanelHeader title={title} copyValue={output ?? null} />
      {output ? (
        <pre className="overflow-x-auto rounded-lg border border-marketing-border bg-marketing-surface-translucent p-3 text-xs whitespace-pre-wrap text-marketing-text-primary">
          {output}
        </pre>
      ) : (
        <div className="rounded-lg border border-dashed border-marketing-border bg-marketing-surface-translucent p-3 text-xs text-marketing-text-muted">
          {emptyLabel}
        </div>
      )}
    </section>
  );
}

export function MetadataPanel({
  title,
  items,
  emptyLabel,
}: MetadataPanelProps) {
  const visibleItems = items.filter((item) => Boolean(item.value));

  return (
    <section>
      <PanelHeader title={title} />
      {visibleItems.length > 0 ? (
        <div className="rounded-lg border border-marketing-border bg-marketing-surface-translucent p-3">
          <dl className="space-y-2 text-xs">
            {visibleItems.map((item) => (
              <div
                key={item.label}
                className="flex items-start justify-between gap-3"
              >
                <dt className="text-marketing-text-muted">{item.label}</dt>
                <dd className="max-w-[70%] break-words text-right text-marketing-text-primary">
                  {item.value}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-marketing-border bg-marketing-surface-translucent p-3 text-xs text-marketing-text-muted">
          {emptyLabel}
        </div>
      )}
    </section>
  );
}
