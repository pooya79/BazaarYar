import type {
  AggregateFunction,
  FilterOperator,
  SortDirection,
} from "@/lib/api/schemas/tables";

export type FilterDraft = {
  id: string;
  field: string;
  op: FilterOperator;
  value: string;
};

export type SortDraft = {
  id: string;
  field: string;
  direction: SortDirection;
};

export type AggregateDraft = {
  id: string;
  function: AggregateFunction;
  field: string;
  alias: string;
};

export type QueuedUpsert = {
  client_id: string;
  row_id?: string;
  values_json: Record<string, unknown>;
};

export const pageSizeOptions = [25, 50, 100, 200];

export const filterOperatorOptions: Array<{
  value: FilterOperator;
  label: string;
  requiresValue: boolean;
}> = [
  { value: "eq", label: "Equals", requiresValue: true },
  { value: "neq", label: "Not equal", requiresValue: true },
  { value: "gt", label: "Greater than", requiresValue: true },
  { value: "gte", label: "Greater or equal", requiresValue: true },
  { value: "lt", label: "Less than", requiresValue: true },
  { value: "lte", label: "Less or equal", requiresValue: true },
  { value: "in", label: "In list", requiresValue: true },
  { value: "contains", label: "Contains", requiresValue: true },
  { value: "starts_with", label: "Starts with", requiresValue: true },
  { value: "ends_with", label: "Ends with", requiresValue: true },
  { value: "is_null", label: "Is null", requiresValue: false },
  { value: "not_null", label: "Not null", requiresValue: false },
];

export const aggregateFunctionOptions: Array<{
  value: AggregateFunction;
  label: string;
  requiresField: boolean;
}> = [
  { value: "count", label: "Count", requiresField: false },
  { value: "sum", label: "Sum", requiresField: true },
  { value: "avg", label: "Average", requiresField: true },
  { value: "min", label: "Min", requiresField: true },
  { value: "max", label: "Max", requiresField: true },
];

export const fieldClass =
  "h-9 w-full rounded-lg border border-marketing-border bg-marketing-surface px-3 text-sm text-marketing-text-primary outline-none transition-colors focus:border-marketing-primary";

export const panelClass =
  "rounded-2xl border border-marketing-border bg-marketing-surface p-4 shadow-marketing-subtle";

export const newDraftId = (prefix: string) =>
  `${prefix}-${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
