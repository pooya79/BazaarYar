import {
  ArrowUpRight,
  Download,
  MoreHorizontal,
  Pencil,
  Plus,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { ReferenceTableSummary } from "@/lib/api/schemas/tables";
import { cn } from "@/lib/utils";
import { formatDateTime } from "@/view/referenceTables/utils";

type ReferenceTablesViewProps = {
  tables: ReferenceTableSummary[];
  tableMenuOpenId: string | null;
  exportingTableId: string | null;
  deletingTableId: string | null;
  onTableMenuOpenChange: (tableId: string | null) => void;
  onCreateTable: () => void;
  onOpenTable: (tableId: string) => void;
  onEditTable: (table: ReferenceTableSummary) => void;
  onDeleteTable: (table: ReferenceTableSummary) => void;
  onExportTable: (table: ReferenceTableSummary) => void;
};

const tableMenuItemClass = "cursor-pointer rounded-lg px-2.5 py-2";

export function ReferenceTablesView({
  tables,
  tableMenuOpenId,
  exportingTableId,
  deletingTableId,
  onTableMenuOpenChange,
  onCreateTable,
  onOpenTable,
  onEditTable,
  onDeleteTable,
  onExportTable,
}: ReferenceTablesViewProps) {
  const totalRows = tables.reduce((sum, table) => sum + table.row_count, 0);
  const latestUpdatedAt = tables
    .map((table) => new Date(table.updated_at).getTime())
    .filter((value) => Number.isFinite(value))
    .reduce<number | null>((latest, value) => {
      if (latest === null || value > latest) {
        return value;
      }
      return latest;
    }, null);

  const summaryCards = [
    {
      label: "Total tables",
      value: tables.length.toLocaleString(),
      helper: "Reference datasets",
    },
    {
      label: "Total rows",
      value: totalRows.toLocaleString(),
      helper: "Queryable records",
    },
    {
      label: "Last update",
      value:
        latestUpdatedAt === null
          ? "-"
          : formatDateTime(new Date(latestUpdatedAt).toISOString()),
      helper: "Most recently updated table",
    },
  ];

  return (
    <div className="flex flex-1 flex-col overflow-y-auto p-4 md:p-8">
      <div className="flex flex-col gap-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <h2 className="text-2xl font-semibold text-marketing-text-primary">
              Reference Tables
            </h2>
            <p className="max-w-3xl text-sm text-marketing-text-secondary">
              Build trusted tables for campaign analytics and consistent
              decision support. Agent access will be enabled when table tools
              are active in runtime.
            </p>
          </div>
          <Button
            type="button"
            className={cn(
              "h-11 rounded-xl px-4 text-sm font-semibold text-marketing-on-primary shadow-marketing-soft transition-all",
              "bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to",
              "hover:-translate-y-0.5 hover:shadow-marketing-hover",
            )}
            onClick={onCreateTable}
          >
            <Plus className="size-4" aria-hidden="true" />
            Create table
          </Button>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          {summaryCards.map((card) => (
            <div
              key={card.label}
              className="rounded-2xl border border-marketing-border bg-marketing-surface p-4 shadow-marketing-subtle"
            >
              <div className="text-xs font-semibold uppercase tracking-[1.2px] text-marketing-text-muted">
                {card.label}
              </div>
              <div className="mt-2 text-2xl font-semibold text-marketing-text-primary">
                {card.value}
              </div>
              <div className="mt-1 text-xs text-marketing-text-secondary">
                {card.helper}
              </div>
            </div>
          ))}
        </div>

        <div className="rounded-2xl border border-marketing-border bg-marketing-accent-soft px-4 py-3 text-sm text-marketing-text-secondary">
          Agent access available when table tools are enabled.
        </div>

        {tables.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-marketing-border bg-marketing-surface p-10 text-center shadow-marketing-subtle">
            <h3 className="text-lg font-semibold text-marketing-text-primary">
              No reference tables yet
            </h3>
            <p className="mt-2 text-sm text-marketing-text-secondary">
              Create your first table to start querying structured campaign
              data.
            </p>
            <Button
              type="button"
              className={cn(
                "mt-6 h-10 rounded-xl px-4 text-sm font-semibold text-marketing-on-primary",
                "bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to",
              )}
              onClick={onCreateTable}
            >
              <Plus className="size-4" aria-hidden="true" />
              Create first table
            </Button>
          </div>
        ) : (
          <div className="grid gap-5 xl:grid-cols-2">
            {tables.map((table) => (
              <div
                key={table.id}
                className="rounded-2xl border border-marketing-border bg-marketing-surface p-5 shadow-marketing-subtle transition-all duration-200 hover:-translate-y-1 hover:border-marketing-secondary hover:shadow-marketing-soft"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h3 className="truncate text-lg font-semibold text-marketing-text-primary">
                      {table.title?.trim() || table.name}
                    </h3>
                    <p className="mt-1 break-all text-xs font-semibold uppercase tracking-[1.2px] text-marketing-text-muted">
                      {table.name}
                    </p>
                    <p className="mt-2 text-sm text-marketing-text-secondary">
                      {table.description?.trim() ||
                        "No description provided for this table."}
                    </p>
                  </div>

                  <DropdownMenu
                    open={tableMenuOpenId === table.id}
                    onOpenChange={(open) =>
                      onTableMenuOpenChange(open ? table.id : null)
                    }
                  >
                    <DropdownMenuTrigger asChild>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-9 w-9 rounded-lg text-marketing-text-muted hover:bg-marketing-accent-medium hover:text-marketing-primary"
                        aria-label="Table actions"
                      >
                        <MoreHorizontal className="size-5" aria-hidden="true" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      sideOffset={8}
                      className="min-w-[180px] rounded-[10px] border-marketing-border bg-marketing-surface p-1.5 text-marketing-text-primary shadow-marketing-soft"
                    >
                      <DropdownMenuItem
                        className={cn(
                          tableMenuItemClass,
                          "focus:bg-marketing-accent-soft focus:text-marketing-primary",
                        )}
                        onSelect={() => onOpenTable(table.id)}
                      >
                        <ArrowUpRight className="size-4 text-marketing-text-primary" />
                        <span>Open table</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className={cn(
                          tableMenuItemClass,
                          "focus:bg-marketing-accent-soft focus:text-marketing-primary",
                        )}
                        onSelect={() => onEditTable(table)}
                      >
                        <Pencil className="size-4 text-marketing-text-primary" />
                        <span>Edit metadata</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className={cn(
                          tableMenuItemClass,
                          "focus:bg-marketing-accent-soft focus:text-marketing-primary",
                        )}
                        onSelect={() => onExportTable(table)}
                        disabled={exportingTableId === table.id}
                      >
                        <Download className="size-4 text-marketing-text-primary" />
                        <span>
                          {exportingTableId === table.id
                            ? "Exporting..."
                            : "Export CSV"}
                        </span>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        variant="destructive"
                        className={cn(
                          tableMenuItemClass,
                          "focus:bg-marketing-danger-soft focus:text-marketing-danger",
                        )}
                        onSelect={() => onDeleteTable(table)}
                        disabled={deletingTableId === table.id}
                      >
                        <Trash2 className="size-4 text-marketing-danger" />
                        <span>
                          {deletingTableId === table.id
                            ? "Deleting..."
                            : "Delete table"}
                        </span>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {[
                    {
                      label: "Rows",
                      value: table.row_count.toLocaleString(),
                    },
                    {
                      label: "Created",
                      value: formatDateTime(table.created_at),
                    },
                    {
                      label: "Updated",
                      value: formatDateTime(table.updated_at),
                    },
                    {
                      label: "Table ID",
                      value: table.id,
                    },
                  ].map((item) => (
                    <div
                      key={`${table.id}-${item.label}`}
                      className="rounded-xl border border-marketing-border bg-marketing-accent-soft px-3 py-2"
                    >
                      <div className="text-xs uppercase tracking-[1px] text-marketing-text-muted">
                        {item.label}
                      </div>
                      <div className="truncate text-sm font-semibold text-marketing-text-primary">
                        {item.value}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-4">
                  <Button
                    type="button"
                    variant="outline"
                    className="h-9 rounded-lg border-marketing-border bg-marketing-surface text-marketing-text-primary hover:bg-marketing-accent-soft"
                    onClick={() => onOpenTable(table.id)}
                  >
                    Open table
                    <ArrowUpRight className="size-4" aria-hidden="true" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
