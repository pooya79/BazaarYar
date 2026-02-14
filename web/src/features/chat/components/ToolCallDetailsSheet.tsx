import type { ToolCallEntry } from "@/features/chat/model/types";
import {
  buildPythonToolViewModel,
  isPythonToolCall,
} from "@/features/chat/utils/chatViewUtils";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/shared/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
import { MessageAttachments } from "./MessageAttachments";
import { MetadataPanel, OutputPanel, PythonCodePanel } from "./ToolCallPanels";

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

function RawSection({
  title,
  content,
  emptyLabel,
}: {
  title: string;
  content: string | null | undefined;
  emptyLabel: string;
}) {
  return (
    <section className="space-y-2">
      <h4 className="text-[0.7rem] font-semibold uppercase tracking-[0.08em] text-marketing-text-muted">
        {title}
      </h4>
      {content ? (
        <pre className="overflow-x-auto rounded-lg border border-marketing-border bg-marketing-surface-translucent p-3 text-xs whitespace-pre-wrap text-marketing-text-primary">
          {content}
        </pre>
      ) : (
        <div className="rounded-lg border border-dashed border-marketing-border bg-marketing-surface-translucent p-3 text-xs text-marketing-text-muted">
          {emptyLabel}
        </div>
      )}
    </section>
  );
}

function ToolCallHeader({ toolCall }: { toolCall: ToolCallEntry }) {
  return (
    <section className="space-y-2">
      <h3 className="text-[0.7rem] font-semibold uppercase tracking-[0.08em] text-marketing-text-muted">
        Tool Call
      </h3>
      <div className="rounded-lg border border-marketing-border bg-marketing-surface-translucent p-3 text-xs text-marketing-text-secondary">
        <div>name: {displayToolName(toolCall.name)}</div>
        {toolCall.callType ? <div>call_type: {toolCall.callType}</div> : null}
        {toolCall.callId ? <div>id: {toolCall.callId}</div> : null}
      </div>
    </section>
  );
}

function RowList({
  title,
  rows,
  emptyLabel,
}: {
  title: string;
  rows: string[];
  emptyLabel: string;
}) {
  return (
    <section className="space-y-2">
      <h4 className="text-[0.7rem] font-semibold uppercase tracking-[0.08em] text-marketing-text-muted">
        {title}
      </h4>
      {rows.length > 0 ? (
        <div className="rounded-lg border border-marketing-border bg-marketing-surface-translucent p-3">
          <ul className="space-y-1 text-xs text-marketing-text-primary">
            {rows.map((row, index) => (
              <li key={`${index}-${row}`} className="break-words">
                {row}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-marketing-border bg-marketing-surface-translucent p-3 text-xs text-marketing-text-muted">
          {emptyLabel}
        </div>
      )}
    </section>
  );
}

export function ToolCallDetailsSheet({
  open,
  onOpenChange,
  toolCall,
  turnTime,
}: ToolCallDetailsSheetProps) {
  const pythonView =
    toolCall && isPythonToolCall(toolCall)
      ? buildPythonToolViewModel(toolCall)
      : null;

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
          {!toolCall ? null : pythonView ? (
            <Tabs defaultValue="overview" className="w-full">
              <TabsList
                variant="line"
                className="h-auto w-full flex-wrap gap-1 border-b border-marketing-border bg-transparent p-0 pb-1"
              >
                <TabsTrigger
                  value="overview"
                  className="h-7 flex-none rounded-md px-2 text-[0.68rem] text-marketing-text-muted data-[state=active]:text-marketing-text-primary"
                >
                  Overview
                </TabsTrigger>
                <TabsTrigger
                  value="artifacts"
                  className="h-7 flex-none rounded-md px-2 text-[0.68rem] text-marketing-text-muted data-[state=active]:text-marketing-text-primary"
                >
                  Artifacts
                </TabsTrigger>
                <TabsTrigger
                  value="raw"
                  className="h-7 flex-none rounded-md px-2 text-[0.68rem] text-marketing-text-muted data-[state=active]:text-marketing-text-primary"
                >
                  Raw
                </TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="mt-3 space-y-4">
                <ToolCallHeader toolCall={toolCall} />

                <MetadataPanel
                  title="Execution Metadata"
                  items={[
                    { label: "status", value: pythonView.status },
                    { label: "summary", value: pythonView.summary },
                    {
                      label: "sandbox_session_id",
                      value: pythonView.sandboxSessionId,
                    },
                    {
                      label: "sandbox_reused",
                      value: pythonView.sandboxReused,
                    },
                    {
                      label: "request_sequence",
                      value: pythonView.requestSequence,
                    },
                    { label: "queue_wait_ms", value: pythonView.queueWaitMs },
                  ]}
                  emptyLabel="No execution metadata available."
                />

                <RowList
                  title="Input Files"
                  rows={pythonView.inputFiles}
                  emptyLabel="No input files captured."
                />

                <PythonCodePanel
                  title="Python Code"
                  code={pythonView.code}
                  emptyLabel="Code argument was not provided."
                />

                <OutputPanel
                  title="Stdout"
                  output={pythonView.stdout}
                  emptyLabel="No stdout captured."
                />

                <OutputPanel
                  title="Stderr"
                  output={pythonView.stderr}
                  emptyLabel="No stderr captured."
                />
              </TabsContent>

              <TabsContent value="artifacts" className="mt-3 space-y-4">
                <RowList
                  title="Artifact Attachments"
                  rows={pythonView.artifactAttachments}
                  emptyLabel="No artifact metadata captured."
                />
                {toolCall.resultArtifacts &&
                toolCall.resultArtifacts.length > 0 ? (
                  <MessageAttachments attachments={toolCall.resultArtifacts} />
                ) : (
                  <div className="rounded-lg border border-dashed border-marketing-border bg-marketing-surface-translucent p-3 text-xs text-marketing-text-muted">
                    No downloadable artifacts.
                  </div>
                )}
              </TabsContent>

              <TabsContent value="raw" className="mt-3 space-y-4">
                <RawSection
                  title="Arguments (Stream)"
                  content={pythonView.rawArgs}
                  emptyLabel="No arguments streamed."
                />
                <RawSection
                  title="Arguments (Final JSON)"
                  content={pythonView.rawFinalArgs}
                  emptyLabel="No final arguments captured."
                />
                <RawSection
                  title="Result Content (Raw)"
                  content={pythonView.rawResult}
                  emptyLabel="Waiting for tool result..."
                />
              </TabsContent>
            </Tabs>
          ) : (
            <div className="space-y-4">
              <ToolCallHeader toolCall={toolCall} />

              <RawSection
                title="Arguments (Stream)"
                content={toolCall.streamedArgsText}
                emptyLabel="No arguments streamed."
              />
              <RawSection
                title="Arguments (Final JSON)"
                content={
                  toolCall.finalArgs
                    ? JSON.stringify(toolCall.finalArgs, null, 2)
                    : null
                }
                emptyLabel="No final arguments captured."
              />
              <RawSection
                title="Tool Result"
                content={toolCall.resultContent}
                emptyLabel="Waiting for tool result..."
              />
              {toolCall.resultArtifacts &&
              toolCall.resultArtifacts.length > 0 ? (
                <MessageAttachments attachments={toolCall.resultArtifacts} />
              ) : null}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
