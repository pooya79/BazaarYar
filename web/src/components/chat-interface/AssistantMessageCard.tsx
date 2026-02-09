import { Wrench } from "lucide-react";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { MessageAttachments } from "./MessageAttachments";
import type { AssistantTurn, ToolCallEntry } from "./types";

type AssistantMessageCardProps = {
  turn: AssistantTurn;
  onToolSelect: (toolKey: string) => void;
};

function getTokenValue(
  usage: Record<string, unknown> | null | undefined,
  keys: string[],
) {
  if (!usage) {
    return null;
  }
  for (const key of keys) {
    const value = usage[key];
    if (typeof value === "number") {
      return value;
    }
  }
  return null;
}

function getModelName(metadata: Record<string, unknown> | null | undefined) {
  if (!metadata) {
    return null;
  }
  for (const key of ["model_name", "model", "modelName"]) {
    const value = metadata[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return null;
}

function buildFooter(turn: AssistantTurn) {
  const parts = [turn.time];

  const inputTokens = getTokenValue(turn.usage, [
    "input_tokens",
    "prompt_tokens",
  ]);
  const outputTokens = getTokenValue(turn.usage, [
    "output_tokens",
    "completion_tokens",
  ]);
  const totalTokens = getTokenValue(turn.usage, ["total_tokens"]);

  if (inputTokens !== null) {
    parts.push(`in ${inputTokens}`);
  }
  if (outputTokens !== null) {
    parts.push(`out ${outputTokens}`);
  }
  if (totalTokens !== null) {
    parts.push(`total ${totalTokens}`);
  }
  if (turn.reasoningTokens !== null && turn.reasoningTokens !== undefined) {
    parts.push(`reasoning ${turn.reasoningTokens}`);
  }

  const modelName = getModelName(turn.responseMetadata);
  if (modelName) {
    parts.push(`model ${modelName}`);
  }

  return parts.join(" · ");
}

function statusLabel(status: ToolCallEntry["status"]) {
  if (status === "streaming") {
    return "streaming";
  }
  if (status === "completed") {
    return "completed";
  }
  return "called";
}

function displayToolName(name: string) {
  return name === "unknown" ? "Tool call" : name;
}

function ToolCallRow({
  tool,
  onClick,
}: {
  tool: ToolCallEntry;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={cn(
        "w-full rounded-lg border border-marketing-border bg-marketing-surface-translucent px-3 py-2 text-left",
        "transition-colors hover:bg-marketing-accent-medium/50 focus-visible:ring-2 focus-visible:ring-marketing-primary focus-visible:outline-none",
      )}
      onClick={onClick}
    >
      <div className="flex items-center gap-2 text-xs text-marketing-text-primary">
        <Wrench className="size-3.5" aria-hidden="true" />
        <span className="truncate font-semibold">
          {displayToolName(tool.name)}
        </span>
        <span className="ml-auto uppercase tracking-[0.08em] text-[0.62rem] text-marketing-text-muted">
          {statusLabel(tool.status)}
        </span>
      </div>
      {tool.callId ? (
        <div className="mt-1 truncate text-[0.65rem] text-marketing-text-muted">
          {tool.callId}
        </div>
      ) : null}
    </button>
  );
}

export function AssistantMessageCard({
  turn,
  onToolSelect,
}: AssistantMessageCardProps) {
  const footer = buildFooter(turn);

  return (
    <Card className="gap-0 rounded-xl rounded-bl-[4px] border-marketing-border bg-marketing-surface py-0 text-marketing-text-primary shadow-marketing-subtle">
      <CardContent className="space-y-3 px-4 py-3.5 text-[0.9375rem] leading-relaxed">
        {turn.answerText ? (
          <div className="whitespace-pre-line">{turn.answerText}</div>
        ) : null}

        {turn.reasoningText ? (
          <div className="rounded-lg border border-dashed border-marketing-border bg-marketing-surface-translucent px-3 py-2 text-xs whitespace-pre-line text-marketing-text-secondary">
            {turn.reasoningText}
          </div>
        ) : null}

        {turn.toolCalls.length > 0 ? (
          <div className="space-y-2">
            <div className="text-[0.65rem] uppercase tracking-[0.08em] text-marketing-text-muted">
              Tool calls
            </div>
            <div className="space-y-2">
              {turn.toolCalls.map((tool) => (
                <ToolCallRow
                  key={tool.key}
                  tool={tool}
                  onClick={() => onToolSelect(tool.key)}
                />
              ))}
            </div>
          </div>
        ) : null}

        {turn.notes.length > 0
          ? turn.notes.map((note, index) => (
              <pre
                key={`${turn.id}:note:${index}`}
                className="overflow-x-auto rounded-lg border border-dashed border-marketing-border bg-marketing-surface-translucent px-3 py-2 text-xs whitespace-pre-wrap text-marketing-text-muted"
              >
                {note}
              </pre>
            ))
          : null}

        <MessageAttachments attachments={turn.attachments} />
      </CardContent>
      <CardFooter className="border-t border-marketing-border px-4 py-2 text-[0.65rem] text-marketing-text-muted">
        {footer}
      </CardFooter>
    </Card>
  );
}
