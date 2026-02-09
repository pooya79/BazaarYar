import { Button } from "@/shared/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/shared/ui/sheet";
import { Textarea } from "@/shared/ui/textarea";

type RowEditorSheetProps = {
  open: boolean;
  rowId: string | null;
  rowJson: string;
  rowError: string | null;
  onOpenChange: (open: boolean) => void;
  onRowJsonChange: (value: string) => void;
  onSave: () => void;
};

export function RowEditorSheet({
  open,
  rowId,
  rowJson,
  rowError,
  onOpenChange,
  onRowJsonChange,
  onSave,
}: RowEditorSheetProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full max-w-xl border-marketing-border bg-marketing-surface p-0 sm:max-w-xl"
      >
        <SheetHeader className="border-b border-marketing-border">
          <SheetTitle className="text-marketing-text-primary">
            {rowId ? "Queue row update" : "Queue new row"}
          </SheetTitle>
          <SheetDescription className="text-marketing-text-secondary">
            Edit row payload as JSON object using table column names.
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-4 p-4">
          <Textarea
            value={rowJson}
            onChange={(event) => onRowJsonChange(event.target.value)}
            className="min-h-[320px] border-marketing-border font-mono text-xs text-marketing-text-primary"
          />

          {rowError && (
            <div className="rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
              {rowError}
            </div>
          )}

          <SheetFooter className="border-t border-marketing-border px-0 pb-0">
            <Button
              type="button"
              variant="outline"
              className="border-marketing-border"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
              onClick={onSave}
            >
              Queue row
            </Button>
          </SheetFooter>
        </div>
      </SheetContent>
    </Sheet>
  );
}
