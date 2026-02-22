import type { ComponentPropsWithoutRef } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import { cn } from "@/shared/lib/utils";

type AssistantMarkdownProps = {
  content: string;
};

type TableAlignment = "left" | "center" | "right" | null;

type ParsedMarkdownTable = {
  header: string[];
  alignments: TableAlignment[];
  rows: string[][];
};

type MarkdownBlock =
  | { type: "markdown"; content: string }
  | { type: "table"; table: ParsedMarkdownTable };

type KeyedItem<T> = {
  key: string;
  value: T;
};

function hashString(value: string): string {
  let hash = 0;
  for (const character of value) {
    hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  }
  return hash.toString(16);
}

function withContentKeys<T>(
  values: T[],
  serialize: (value: T) => string,
  prefix: string,
): KeyedItem<T>[] {
  const seenHashes = new Map<string, number>();

  return values.map((value) => {
    const hash = hashString(serialize(value));
    const keyBase = `${prefix}-${hash}`;
    const duplicateCount = (seenHashes.get(keyBase) ?? 0) + 1;
    seenHashes.set(keyBase, duplicateCount);

    return {
      key: `${keyBase}-${duplicateCount}`,
      value,
    };
  });
}

function splitTableRow(line: string): string[] | null {
  if (!line.includes("|")) {
    return null;
  }

  let trimmed = line.trim();
  if (trimmed.startsWith("|")) {
    trimmed = trimmed.slice(1);
  }
  if (trimmed.endsWith("|")) {
    trimmed = trimmed.slice(0, -1);
  }

  const cells: string[] = [];
  let currentCell = "";
  let isEscaped = false;

  for (const character of trimmed) {
    if (isEscaped) {
      currentCell += character;
      isEscaped = false;
      continue;
    }

    if (character === "\\") {
      currentCell += character;
      isEscaped = true;
      continue;
    }

    if (character === "|") {
      cells.push(currentCell.trim());
      currentCell = "";
      continue;
    }

    currentCell += character;
  }

  cells.push(currentCell.trim());
  return cells;
}

function normalizeTableCells(cells: string[], targetLength: number): string[] {
  if (cells.length === targetLength) {
    return cells;
  }
  if (cells.length > targetLength) {
    return cells.slice(0, targetLength);
  }
  return [
    ...cells,
    ...Array.from({ length: targetLength - cells.length }, () => ""),
  ];
}

function isTableSeparatorCell(cell: string): boolean {
  return /^:?-{3,}:?$/.test(cell.trim());
}

function parseTableAlignment(cell: string): TableAlignment {
  const trimmed = cell.trim();
  const hasLeftAlign = trimmed.startsWith(":");
  const hasRightAlign = trimmed.endsWith(":");

  if (hasLeftAlign && hasRightAlign) {
    return "center";
  }
  if (hasRightAlign) {
    return "right";
  }
  if (hasLeftAlign) {
    return "left";
  }
  return null;
}

function tryParseMarkdownTable(
  lines: string[],
  startIndex: number,
): { table: ParsedMarkdownTable; nextIndex: number } | null {
  const headerRow = lines[startIndex];
  const separatorRow = lines[startIndex + 1];
  if (!headerRow || !separatorRow) {
    return null;
  }

  const headerCells = splitTableRow(headerRow);
  const separatorCells = splitTableRow(separatorRow);
  if (!headerCells || !separatorCells || headerCells.length === 0) {
    return null;
  }

  const normalizedSeparatorCells = normalizeTableCells(
    separatorCells,
    headerCells.length,
  );
  if (!normalizedSeparatorCells.every(isTableSeparatorCell)) {
    return null;
  }

  const alignments = normalizedSeparatorCells.map(parseTableAlignment);
  const rows: string[][] = [];
  let rowIndex = startIndex + 2;

  while (rowIndex < lines.length) {
    const line = lines[rowIndex];
    if (!line || line.trim().length === 0) {
      break;
    }

    const rowCells = splitTableRow(line);
    if (!rowCells) {
      break;
    }

    rows.push(normalizeTableCells(rowCells, headerCells.length));
    rowIndex += 1;
  }

  return {
    table: {
      header: normalizeTableCells(headerCells, headerCells.length),
      alignments,
      rows,
    },
    nextIndex: rowIndex,
  };
}

function parseMarkdownBlocks(content: string): MarkdownBlock[] {
  const lines = content.split("\n");
  const blocks: MarkdownBlock[] = [];
  const markdownBuffer: string[] = [];
  let codeFenceMarker: "```" | "~~~" | null = null;

  const flushMarkdownBuffer = () => {
    const markdown = markdownBuffer.join("\n");
    if (markdown.trim().length > 0) {
      blocks.push({ type: "markdown", content: markdown });
    }
    markdownBuffer.length = 0;
  };

  for (let lineIndex = 0; lineIndex < lines.length; ) {
    const currentLine = lines[lineIndex] ?? "";
    const trimmedLine = currentLine.trimStart();

    if (codeFenceMarker !== null) {
      markdownBuffer.push(currentLine);
      if (trimmedLine.startsWith(codeFenceMarker)) {
        codeFenceMarker = null;
      }
      lineIndex += 1;
      continue;
    }

    if (trimmedLine.startsWith("```") || trimmedLine.startsWith("~~~")) {
      markdownBuffer.push(currentLine);
      codeFenceMarker = trimmedLine.startsWith("```") ? "```" : "~~~";
      lineIndex += 1;
      continue;
    }

    const parsedTable = tryParseMarkdownTable(lines, lineIndex);
    if (parsedTable) {
      flushMarkdownBuffer();
      blocks.push({ type: "table", table: parsedTable.table });
      lineIndex = parsedTable.nextIndex;
      continue;
    }

    markdownBuffer.push(currentLine);
    lineIndex += 1;
  }

  flushMarkdownBuffer();
  return blocks.length > 0 ? blocks : [{ type: "markdown", content }];
}

function alignmentClassName(alignment: TableAlignment): string {
  switch (alignment) {
    case "right":
      return "text-right";
    case "center":
      return "text-center";
    default:
      return "text-left";
  }
}

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
  const blocks = parseMarkdownBlocks(content);
  const keyedBlocks = withContentKeys(
    blocks,
    (block) =>
      block.type === "markdown"
        ? block.content
        : [
            block.table.header.join("\u001F"),
            block.table.rows.map((row) => row.join("\u001F")).join("\u001E"),
          ].join("\u001D"),
    "assistant-markdown-block",
  );

  return (
    <div className="space-y-3 break-words">
      {keyedBlocks.map(({ key: blockKey, value: block }) => {
        if (block.type === "markdown") {
          return (
            <ReactMarkdown key={blockKey} components={markdownComponents}>
              {block.content}
            </ReactMarkdown>
          );
        }

        const keyedHeaderCells = withContentKeys(
          block.table.header,
          (cell) => cell,
          `${blockKey}-header-cell`,
        );
        const keyedRows = withContentKeys(
          block.table.rows,
          (row) => row.join("\u001F"),
          `${blockKey}-row`,
        );

        return (
          <div
            key={blockKey}
            className="my-2 overflow-x-auto rounded-lg border border-marketing-border"
          >
            <table className="w-full min-w-[20rem] border-collapse text-sm text-marketing-text-primary">
              <thead className="bg-marketing-surface-translucent">
                <tr>
                  {keyedHeaderCells.map(
                    ({ key: headerKey, value: cell }, cellIndex) => (
                      <th
                        key={headerKey}
                        className={cn(
                          "border-b border-marketing-border px-3 py-2 align-top font-semibold",
                          alignmentClassName(
                            block.table.alignments[cellIndex] ?? null,
                          ),
                          "[&_blockquote]:my-1 [&_ol]:my-1 [&_p]:my-0 [&_pre]:my-1 [&_ul]:my-1",
                        )}
                      >
                        <ReactMarkdown components={markdownComponents}>
                          {cell}
                        </ReactMarkdown>
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {keyedRows.map(({ key: rowKey, value: row }) => {
                  const keyedCells = withContentKeys(
                    row,
                    (cell) => cell,
                    `${rowKey}-cell`,
                  );

                  return (
                    <tr
                      key={rowKey}
                      className="even:bg-marketing-surface-translucent/40"
                    >
                      {keyedCells.map(
                        ({ key: cellKey, value: cell }, cellIndex) => (
                          <td
                            key={cellKey}
                            className={cn(
                              "border-b border-marketing-border px-3 py-2 align-top last:border-b",
                              alignmentClassName(
                                block.table.alignments[cellIndex] ?? null,
                              ),
                              "[&_blockquote]:my-1 [&_ol]:my-1 [&_p]:my-0 [&_pre]:my-1 [&_ul]:my-1",
                            )}
                          >
                            <ReactMarkdown components={markdownComponents}>
                              {cell}
                            </ReactMarkdown>
                          </td>
                        ),
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}
