import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MinusCircle, MoreHorizontal, Plus, Power, Trash2 } from "lucide-react";

export type ReferenceTableStatus = "active" | "disabled";

export type ReferenceTable = {
  id: string;
  name: string;
  description: string;
  rows: number;
  columns: number;
  source: string;
  refresh: string;
  updatedAt: string;
  status: ReferenceTableStatus;
  assignedAgents: string[];
  tags: string[];
};

export type ReferenceTableAction = "toggle" | "remove" | "delete";

type ReferenceTablesViewProps = {
  tables: ReferenceTable[];
  tableMenuOpenId: string | null;
  onTableMenuOpenChange: (tableId: string | null) => void;
  onAddTable: () => void;
  onTableAction: (action: ReferenceTableAction, tableId: string) => void;
};

const tableStatusLabels: Record<ReferenceTableStatus, string> = {
  active: "Active",
  disabled: "Disabled",
};

const tableStatusClasses: Record<ReferenceTableStatus, string> = {
  active: "bg-marketing-status-active text-marketing-on-primary",
  disabled: "bg-marketing-border text-marketing-text-muted",
};

const tableMenuItemClass = "cursor-pointer rounded-lg px-2.5 py-2";

export const initialReferenceTables: ReferenceTable[] = [
  {
    id: "product-faq",
    name: "Product FAQ",
    description:
      "Approved answers for feature, pricing, and roadmap questions.",
    rows: 128,
    columns: 12,
    source: "Notion sync",
    refresh: "Hourly",
    updatedAt: "Jan 30, 2026",
    status: "active",
    assignedAgents: ["Support Copilot", "Website Concierge"],
    tags: ["faq", "approved", "public"],
  },
  {
    id: "pricing-rules",
    name: "Pricing Rules",
    description:
      "Tier logic, discounts, and eligibility guardrails for sales outreach.",
    rows: 36,
    columns: 9,
    source: "Salesforce",
    refresh: "Daily",
    updatedAt: "Jan 28, 2026",
    status: "active",
    assignedAgents: ["Sales Agent"],
    tags: ["pricing", "legal", "sales"],
  },
  {
    id: "compliance-claims",
    name: "Compliance Claims",
    description:
      "Allowed claims, disclaimers, and regulated phrasing for campaigns.",
    rows: 52,
    columns: 7,
    source: "Manual review",
    refresh: "On demand",
    updatedAt: "Jan 14, 2026",
    status: "disabled",
    assignedAgents: [],
    tags: ["compliance", "risk", "regulated"],
  },
];

export function ReferenceTablesView({
  tables,
  tableMenuOpenId,
  onTableMenuOpenChange,
  onAddTable,
  onTableAction,
}: ReferenceTablesViewProps) {
  const activeTables = tables.filter(
    (table) => table.status === "active",
  ).length;
  const assignedTables = tables.filter(
    (table) => table.assignedAgents.length > 0,
  ).length;

  const summaryCards = [
    {
      label: "Total tables",
      value: tables.length,
      helper: "Canonical sources",
    },
    {
      label: "Active",
      value: activeTables,
      helper: "Available to agents",
    },
    {
      label: "Assigned",
      value: assignedTables,
      helper: "Mapped to workflows",
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
            <p className="max-w-2xl text-sm text-marketing-text-secondary">
              Build trusted tables that agents can consult for approved facts,
              pricing rules, and compliance-safe language.
            </p>
          </div>
          <Button
            type="button"
            className={cn(
              "h-11 rounded-xl px-4 text-sm font-semibold text-marketing-on-primary shadow-marketing-soft transition-all",
              "bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to",
              "hover:-translate-y-0.5 hover:shadow-marketing-hover",
            )}
            onClick={onAddTable}
          >
            <Plus className="size-4" aria-hidden="true" />
            Add table
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
                {card.value.toLocaleString()}
              </div>
              <div className="mt-1 text-xs text-marketing-text-secondary">
                {card.helper}
              </div>
            </div>
          ))}
        </div>

        {tables.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-marketing-border bg-marketing-surface p-10 text-center shadow-marketing-subtle">
            <h3 className="text-lg font-semibold text-marketing-text-primary">
              No reference tables yet
            </h3>
            <p className="mt-2 text-sm text-marketing-text-secondary">
              Add your first table to give agents a trusted source of truth.
            </p>
            <Button
              type="button"
              className={cn(
                "mt-6 h-10 rounded-xl px-4 text-sm font-semibold text-marketing-on-primary",
                "bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to",
              )}
              onClick={onAddTable}
            >
              <Plus className="size-4" aria-hidden="true" />
              Add your first table
            </Button>
          </div>
        ) : (
          <div className="grid gap-5 xl:grid-cols-2">
            {tables.map((table) => (
              <div
                key={table.id}
                className={cn(
                  "rounded-2xl border border-marketing-border bg-marketing-surface p-5 shadow-marketing-subtle transition-all duration-200",
                  table.status === "disabled"
                    ? "opacity-70"
                    : "hover:-translate-y-1 hover:border-marketing-secondary hover:shadow-marketing-soft",
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-semibold text-marketing-text-primary">
                        {table.name}
                      </h3>
                      <span
                        className={cn(
                          "rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.5px]",
                          tableStatusClasses[table.status],
                        )}
                      >
                        {tableStatusLabels[table.status]}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-marketing-text-secondary">
                      {table.description}
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
                      className="min-w-[160px] rounded-[10px] border-marketing-border bg-marketing-surface p-1.5 text-marketing-text-primary shadow-marketing-soft"
                    >
                      <DropdownMenuItem
                        className={cn(
                          tableMenuItemClass,
                          "focus:bg-marketing-accent-soft focus:text-marketing-primary",
                        )}
                        onSelect={() => onTableAction("toggle", table.id)}
                      >
                        <Power className="size-4 text-marketing-text-primary" />
                        <span>
                          {table.status === "active" ? "Disable" : "Enable"}
                        </span>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className={cn(
                          tableMenuItemClass,
                          "focus:bg-marketing-accent-soft focus:text-marketing-primary",
                        )}
                        onSelect={() => onTableAction("remove", table.id)}
                        disabled={table.assignedAgents.length === 0}
                      >
                        <MinusCircle className="size-4 text-marketing-text-primary" />
                        <span>Remove from agents</span>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        variant="destructive"
                        className={cn(
                          tableMenuItemClass,
                          "focus:bg-marketing-danger-soft focus:text-marketing-danger",
                        )}
                        onSelect={() => onTableAction("delete", table.id)}
                      >
                        <Trash2 className="size-4 text-marketing-danger" />
                        <span>Delete</span>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {[
                    { label: "Rows", value: table.rows.toLocaleString() },
                    { label: "Columns", value: table.columns.toString() },
                    { label: "Source", value: table.source },
                    { label: "Updated", value: table.updatedAt },
                  ].map((item) => (
                    <div
                      key={`${table.id}-${item.label}`}
                      className="rounded-xl border border-marketing-border bg-marketing-accent-soft px-3 py-2"
                    >
                      <div className="text-xs uppercase tracking-[1px] text-marketing-text-muted">
                        {item.label}
                      </div>
                      <div className="text-sm font-semibold text-marketing-text-primary">
                        {item.value}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-4 text-xs font-semibold uppercase tracking-[1.2px] text-marketing-text-muted">
                  Used by agents
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {table.assignedAgents.length > 0 ? (
                    table.assignedAgents.map((agent) => (
                      <span
                        key={`${table.id}-${agent}`}
                        className="rounded-full border border-marketing-border bg-marketing-surface px-3 py-1 text-xs font-semibold text-marketing-text-secondary"
                      >
                        {agent}
                      </span>
                    ))
                  ) : (
                    <span className="rounded-full border border-marketing-border bg-marketing-accent-soft px-3 py-1 text-xs font-semibold text-marketing-text-muted">
                      Unassigned
                    </span>
                  )}
                </div>

                <div className="mt-4 flex flex-wrap gap-2 text-xs">
                  {table.tags.map((tag) => (
                    <span
                      key={`${table.id}-${tag}`}
                      className="rounded-full border border-marketing-border bg-marketing-accent-medium px-2.5 py-1 font-semibold text-marketing-primary"
                    >
                      {tag}
                    </span>
                  ))}
                  <span className="rounded-full border border-marketing-border bg-marketing-surface px-2.5 py-1 font-semibold text-marketing-text-secondary">
                    Refresh: {table.refresh}
                  </span>
                </div>

                {table.status === "disabled" && (
                  <div className="mt-4 rounded-xl border border-marketing-border bg-marketing-accent-soft px-3 py-2 text-xs text-marketing-text-secondary">
                    Disabled tables are skipped by agents until re-enabled.
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
