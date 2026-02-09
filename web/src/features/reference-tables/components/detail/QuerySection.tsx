import { Loader2, Play, Plus, Trash2 } from "lucide-react";
import type { Dispatch, SetStateAction } from "react";
import {
  type AggregateDraft,
  aggregateFunctionOptions,
  type FilterDraft,
  fieldClass,
  filterOperatorOptions,
  newDraftId,
  pageSizeOptions,
  panelClass,
  type SortDraft,
} from "@/features/reference-tables/model/queryDrafts";
import type {
  AggregateFunction,
  FilterOperator,
  QueriedRow,
  ReferenceTableDetail,
  RowsQueryResponse,
  SortDirection,
} from "@/shared/api/schemas/tables";
import { Button } from "@/shared/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/ui/select";
import { QueryResultsPanel } from "./QueryResultsPanel";

type QuerySectionProps = {
  table: ReferenceTableDetail;
  filters: FilterDraft[];
  sorts: SortDraft[];
  groupBy: string[];
  aggregates: AggregateDraft[];
  pageSize: number;
  queryResult: RowsQueryResponse | null;
  queryError: string | null;
  isQueryLoading: boolean;
  queuedDeleteSet: Set<string>;
  setFilters: Dispatch<SetStateAction<FilterDraft[]>>;
  setSorts: Dispatch<SetStateAction<SortDraft[]>>;
  setGroupBy: Dispatch<SetStateAction<string[]>>;
  setAggregates: Dispatch<SetStateAction<AggregateDraft[]>>;
  setPageSize: Dispatch<SetStateAction<number>>;
  onRunQuery: (page?: number) => void;
  onResetQuery: () => void;
  onOpenExistingRowEditor: (row: QueriedRow) => void;
  onToggleQueuedDelete: (rowId: string) => void;
};

export function QuerySection({
  table,
  filters,
  sorts,
  groupBy,
  aggregates,
  pageSize,
  queryResult,
  queryError,
  isQueryLoading,
  queuedDeleteSet,
  setFilters,
  setSorts,
  setGroupBy,
  setAggregates,
  setPageSize,
  onRunQuery,
  onResetQuery,
  onOpenExistingRowEditor,
  onToggleQueuedDelete,
}: QuerySectionProps) {
  const canPageBack = (queryResult?.page ?? 1) > 1;
  const canPageForward =
    queryResult !== null &&
    queryResult.page * queryResult.page_size < queryResult.total_rows;

  return (
    <div className={panelClass}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-base font-semibold text-marketing-text-primary">
          Row explorer and query builder
        </h3>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            className="border-marketing-border"
            onClick={onResetQuery}
          >
            Reset query
          </Button>
          <Button
            type="button"
            className="bg-gradient-to-br from-marketing-gradient-from to-marketing-gradient-to text-marketing-on-primary"
            onClick={() => onRunQuery(1)}
            disabled={isQueryLoading}
          >
            {isQueryLoading ? (
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
            ) : (
              <Play className="size-4" aria-hidden="true" />
            )}
            Run query
          </Button>
        </div>
      </div>

      <div className="mt-4 space-y-4">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
              Filters
            </div>
            <Button
              type="button"
              variant="outline"
              className="h-8 border-marketing-border"
              onClick={() => {
                setFilters((prev) => [
                  ...prev,
                  {
                    id: newDraftId("filter"),
                    field: table.columns[0]?.name ?? "",
                    op: "eq",
                    value: "",
                  },
                ]);
              }}
            >
              <Plus className="size-4" aria-hidden="true" />
              Add filter
            </Button>
          </div>

          {filters.length === 0 ? (
            <p className="text-sm text-marketing-text-secondary">
              No filters applied.
            </p>
          ) : (
            <div className="space-y-2">
              {filters.map((filter) => {
                const operator = filterOperatorOptions.find(
                  (item) => item.value === filter.op,
                );

                return (
                  <div
                    key={filter.id}
                    className="grid gap-2 rounded-lg border border-marketing-border bg-marketing-accent-soft p-2 md:grid-cols-[1fr_180px_1fr_auto]"
                  >
                    <Select
                      value={filter.field}
                      onValueChange={(value) => {
                        setFilters((prev) =>
                          prev.map((item) =>
                            item.id === filter.id
                              ? { ...item, field: value }
                              : item,
                          ),
                        );
                      }}
                    >
                      <SelectTrigger className="h-9 w-full border-marketing-border bg-marketing-surface">
                        <SelectValue placeholder="Field" />
                      </SelectTrigger>
                      <SelectContent>
                        {table.columns.map((column) => (
                          <SelectItem key={column.id} value={column.name}>
                            {column.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <Select
                      value={filter.op}
                      onValueChange={(value) => {
                        setFilters((prev) =>
                          prev.map((item) =>
                            item.id === filter.id
                              ? {
                                  ...item,
                                  op: value as FilterOperator,
                                  value:
                                    value === "is_null" || value === "not_null"
                                      ? ""
                                      : item.value,
                                }
                              : item,
                          ),
                        );
                      }}
                    >
                      <SelectTrigger className="h-9 w-full border-marketing-border bg-marketing-surface">
                        <SelectValue placeholder="Operator" />
                      </SelectTrigger>
                      <SelectContent>
                        {filterOperatorOptions.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    {operator?.requiresValue ? (
                      <input
                        className={fieldClass}
                        value={filter.value}
                        onChange={(event) => {
                          const nextValue = event.target.value;
                          setFilters((prev) =>
                            prev.map((item) =>
                              item.id === filter.id
                                ? { ...item, value: nextValue }
                                : item,
                            ),
                          );
                        }}
                        placeholder={
                          filter.op === "in"
                            ? "comma,separated,values"
                            : "value"
                        }
                      />
                    ) : (
                      <div className="flex items-center rounded-lg border border-dashed border-marketing-border bg-marketing-surface px-3 text-sm text-marketing-text-muted">
                        No value required
                      </div>
                    )}

                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-9 w-9 text-marketing-danger hover:bg-marketing-danger-soft"
                      onClick={() => {
                        setFilters((prev) =>
                          prev.filter((item) => item.id !== filter.id),
                        );
                      }}
                    >
                      <Trash2 className="size-4" aria-hidden="true" />
                    </Button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
              Sorts
            </div>
            <Button
              type="button"
              variant="outline"
              className="h-8 border-marketing-border"
              onClick={() => {
                setSorts((prev) => [
                  ...prev,
                  {
                    id: newDraftId("sort"),
                    field: table.columns[0]?.name ?? "",
                    direction: "asc",
                  },
                ]);
              }}
            >
              <Plus className="size-4" aria-hidden="true" />
              Add sort
            </Button>
          </div>

          {sorts.length > 0 && (
            <div className="space-y-2">
              {sorts.map((sort) => (
                <div
                  key={sort.id}
                  className="grid gap-2 rounded-lg border border-marketing-border bg-marketing-accent-soft p-2 md:grid-cols-[1fr_140px_auto]"
                >
                  <Select
                    value={sort.field}
                    onValueChange={(value) => {
                      setSorts((prev) =>
                        prev.map((item) =>
                          item.id === sort.id
                            ? { ...item, field: value }
                            : item,
                        ),
                      );
                    }}
                  >
                    <SelectTrigger className="h-9 w-full border-marketing-border bg-marketing-surface">
                      <SelectValue placeholder="Field" />
                    </SelectTrigger>
                    <SelectContent>
                      {table.columns.map((column) => (
                        <SelectItem key={column.id} value={column.name}>
                          {column.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Select
                    value={sort.direction}
                    onValueChange={(value) => {
                      setSorts((prev) =>
                        prev.map((item) =>
                          item.id === sort.id
                            ? { ...item, direction: value as SortDirection }
                            : item,
                        ),
                      );
                    }}
                  >
                    <SelectTrigger className="h-9 w-full border-marketing-border bg-marketing-surface">
                      <SelectValue placeholder="Direction" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="asc">Ascending</SelectItem>
                      <SelectItem value="desc">Descending</SelectItem>
                    </SelectContent>
                  </Select>

                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-9 w-9 text-marketing-danger hover:bg-marketing-danger-soft"
                    onClick={() => {
                      setSorts((prev) =>
                        prev.filter((item) => item.id !== sort.id),
                      );
                    }}
                  >
                    <Trash2 className="size-4" aria-hidden="true" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
            Group by
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {table.columns.map((column) => {
              const checked = groupBy.includes(column.name);
              return (
                <label
                  key={column.id}
                  className="flex items-center gap-2 rounded-lg border border-marketing-border bg-marketing-accent-soft px-3 py-2 text-sm text-marketing-text-secondary"
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(event) => {
                      const nextChecked = event.target.checked;
                      setGroupBy((prev) =>
                        nextChecked
                          ? [...prev, column.name]
                          : prev.filter((item) => item !== column.name),
                      );
                    }}
                    className="size-4 rounded border-marketing-border"
                  />
                  {column.name}
                </label>
              );
            })}
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
              Aggregates
            </div>
            <Button
              type="button"
              variant="outline"
              className="h-8 border-marketing-border"
              onClick={() => {
                setAggregates((prev) => [
                  ...prev,
                  {
                    id: newDraftId("aggregate"),
                    function: "count",
                    field: "",
                    alias: "",
                  },
                ]);
              }}
            >
              <Plus className="size-4" aria-hidden="true" />
              Add aggregate
            </Button>
          </div>

          {aggregates.length > 0 && (
            <div className="space-y-2">
              {aggregates.map((aggregate) => {
                const functionConfig = aggregateFunctionOptions.find(
                  (item) => item.value === aggregate.function,
                );

                return (
                  <div
                    key={aggregate.id}
                    className="grid gap-2 rounded-lg border border-marketing-border bg-marketing-accent-soft p-2 md:grid-cols-[180px_1fr_1fr_auto]"
                  >
                    <Select
                      value={aggregate.function}
                      onValueChange={(value) => {
                        setAggregates((prev) =>
                          prev.map((item) =>
                            item.id === aggregate.id
                              ? {
                                  ...item,
                                  function: value as AggregateFunction,
                                  field:
                                    value === "count"
                                      ? ""
                                      : item.field ||
                                        table.columns[0]?.name ||
                                        "",
                                }
                              : item,
                          ),
                        );
                      }}
                    >
                      <SelectTrigger className="h-9 w-full border-marketing-border bg-marketing-surface">
                        <SelectValue placeholder="Function" />
                      </SelectTrigger>
                      <SelectContent>
                        {aggregateFunctionOptions.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <Select
                      value={aggregate.field}
                      onValueChange={(value) => {
                        setAggregates((prev) =>
                          prev.map((item) =>
                            item.id === aggregate.id
                              ? { ...item, field: value }
                              : item,
                          ),
                        );
                      }}
                      disabled={!functionConfig?.requiresField}
                    >
                      <SelectTrigger className="h-9 w-full border-marketing-border bg-marketing-surface">
                        <SelectValue
                          placeholder={
                            functionConfig?.requiresField
                              ? "Field"
                              : "Field not required"
                          }
                        />
                      </SelectTrigger>
                      <SelectContent>
                        {table.columns.map((column) => (
                          <SelectItem key={column.id} value={column.name}>
                            {column.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    <input
                      className={fieldClass}
                      value={aggregate.alias}
                      onChange={(event) => {
                        const nextValue = event.target.value;
                        setAggregates((prev) =>
                          prev.map((item) =>
                            item.id === aggregate.id
                              ? { ...item, alias: nextValue }
                              : item,
                          ),
                        );
                      }}
                      placeholder="Alias (optional)"
                    />

                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-9 w-9 text-marketing-danger hover:bg-marketing-danger-soft"
                      onClick={() => {
                        setAggregates((prev) =>
                          prev.filter((item) => item.id !== aggregate.id),
                        );
                      }}
                    >
                      <Trash2 className="size-4" aria-hidden="true" />
                    </Button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-[1px] text-marketing-text-muted">
            Page size
          </span>
          <Select
            value={String(pageSize)}
            onValueChange={(value) => {
              setPageSize(Number(value));
            }}
          >
            <SelectTrigger className="h-9 w-[120px] border-marketing-border bg-marketing-surface">
              <SelectValue placeholder="Page size" />
            </SelectTrigger>
            <SelectContent>
              {pageSizeOptions.map((size) => (
                <SelectItem key={size} value={String(size)}>
                  {size}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {queryError && (
        <div className="mt-4 rounded-lg border border-marketing-danger bg-marketing-danger-soft px-3 py-2 text-sm text-marketing-danger">
          {queryError}
        </div>
      )}

      <div className="mt-4">
        {isQueryLoading ? (
          <div className="rounded-lg border border-marketing-border bg-marketing-accent-soft px-3 py-2 text-sm text-marketing-text-secondary">
            Query in progress...
          </div>
        ) : queryResult ? (
          <QueryResultsPanel
            table={table}
            queryResult={queryResult}
            canPageBack={canPageBack}
            canPageForward={canPageForward}
            queuedDeleteSet={queuedDeleteSet}
            onRunQuery={onRunQuery}
            onOpenExistingRowEditor={onOpenExistingRowEditor}
            onToggleQueuedDelete={onToggleQueuedDelete}
          />
        ) : null}
      </div>
    </div>
  );
}
