import type { ToolCallEntry } from "@/features/chat/model/types";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/shared/ui/sheet";
import { MessageAttachments } from "./MessageAttachments";

type ToolCallDetailsSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  toolCall: ToolCallEntry | null;
  turnTime: string;
};

function formatStatus(status: ToolCallEntry["status"]) {
  if (status === "streaming") return "Streaming";
  if (status === "completed") return "Completed";
  return "Called";
}

function displayToolName(name: string | undefined) {
  if (!name || name === "unknown") {
    return "Tool call";
  }
  return name;
}

export function ToolCallDetailsSheet({
  open,
  onOpenChange,
  toolCall,
  turnTime,
}: ToolCallDetailsSheetProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full border-marketing-border bg-marketing-surface p-0 text-marketing-text-primary sm:max-w-lg"
      >
        <SheetHeader className="border-b border-marketing-border p-4 pr-10">
          <SheetTitle className="text-sm font-semibold text-marketing-text-primary">
            {displayToolName(toolCall?.name)}
          </SheetTitle>
          <SheetDescription className="text-xs text-marketing-text-muted">
            {toolCall ? `${formatStatus(toolCall.status)} · ${turnTime}` : ""}
          </SheetDescription>
        </SheetHeader>

        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-4">
          {!toolCall ? null : (
            <div className="space-y-4">
              <section className="space-y-2">
                <h3 className="text-[0.7rem] font-semibold uppercase tracking-[0.08em] text-marketing-text-muted">
                  Tool Call
                </h3>
                <div className="rounded-lg border border-marketing-border bg-marketing-surface-translucent p-3 text-xs text-marketing-text-secondary">
                  <div>name: {displayToolName(toolCall.name)}</div>
                  {toolCall.callType ? (
                    <div>call_type: {toolCall.callType}</div>
                  ) : null}
                  {toolCall.callId ? <div>id: {toolCall.callId}</div> : null}
                </div>
                {toolCall.streamedArgsText ? (
                  <pre className="overflow-x-auto rounded-lg border border-marketing-border bg-marketing-surface-translucent p-3 text-xs whitespace-pre-wrap text-marketing-text-primary">
                    {toolCall.streamedArgsText}
                  </pre>
                ) : (
                  <div className="rounded-lg border border-dashed border-marketing-border bg-marketing-surface-translucent p-3 text-xs text-marketing-text-muted">
                    No arguments streamed.
                  </div>
                )}
                {toolCall.finalArgs ? (
                  <pre className="overflow-x-auto rounded-lg border border-marketing-border bg-marketing-surface-translucent p-3 text-xs whitespace-pre-wrap text-marketing-text-primary">
                    {JSON.stringify(toolCall.finalArgs, null, 2)}
                  </pre>
                ) : null}
              </section>

              <section className="space-y-2">
                <h3 className="text-[0.7rem] font-semibold uppercase tracking-[0.08em] text-marketing-text-muted">
                  Tool Result
                </h3>
                {toolCall.resultContent ? (
                  <pre className="overflow-x-auto rounded-lg border border-marketing-border bg-marketing-surface-translucent p-3 text-xs whitespace-pre-wrap text-marketing-text-primary">
                    {toolCall.resultContent}
                  </pre>
                ) : (
                  <div className="rounded-lg border border-dashed border-marketing-border bg-marketing-surface-translucent p-3 text-xs text-marketing-text-muted">
                    Waiting for tool result...
                  </div>
                )}
                {toolCall.resultArtifacts &&
                toolCall.resultArtifacts.length > 0 ? (
                  <MessageAttachments attachments={toolCall.resultArtifacts} />
                ) : null}
              </section>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
