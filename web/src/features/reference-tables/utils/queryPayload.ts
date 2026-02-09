import {
  type AggregateDraft,
  aggregateFunctionOptions,
  type FilterDraft,
  type SortDraft,
} from "@/features/reference-tables/model/queryDrafts";
import { parseTypedInputValue } from "@/features/reference-tables/utils/tableUtils";
import type {
  ReferenceTableDetail,
  RowsQueryInput,
} from "@/shared/api/schemas/tables";

type BuildRowsQueryPayloadInput = {
  table: ReferenceTableDetail | null;
  filters: FilterDraft[];
  sorts: SortDraft[];
  groupBy: string[];
  aggregates: AggregateDraft[];
  page: number;
  pageSize: number;
};

export function buildRowsQueryPayload({
  table,
  filters,
  sorts,
  groupBy,
  aggregates,
  page,
  pageSize,
}: BuildRowsQueryPayloadInput): RowsQueryInput {
  if (!table) {
    return {
      filters: [],
      sorts: [],
      group_by: [],
      aggregates: [],
      page,
      page_size: pageSize,
    };
  }

  const columnByName = new Map(
    table.columns.map((column) => [column.name, column]),
  );

  const parsedFilters = filters.map((filter) => {
    if (!filter.field) {
      throw new Error("Select a field for each filter.");
    }

    const column = columnByName.get(filter.field);
    if (!column) {
      throw new Error(`Unknown filter field: ${filter.field}`);
    }

    if (filter.op === "is_null" || filter.op === "not_null") {
      return {
        field: filter.field,
        op: filter.op,
      };
    }

    if (!filter.value.trim()) {
      throw new Error(`Provide a value for filter on ${filter.field}.`);
    }

    if (
      filter.op === "contains" ||
      filter.op === "starts_with" ||
      filter.op === "ends_with"
    ) {
      return {
        field: filter.field,
        op: filter.op,
        value: filter.value,
      };
    }

    if (filter.op === "in") {
      const entries = filter.value
        .split(",")
        .map((entry) => entry.trim())
        .filter(Boolean)
        .map((entry) => parseTypedInputValue(entry, column.data_type));

      if (entries.length === 0) {
        throw new Error(`Provide at least one list value for ${filter.field}.`);
      }

      return {
        field: filter.field,
        op: filter.op,
        value: entries,
      };
    }

    return {
      field: filter.field,
      op: filter.op,
      value: parseTypedInputValue(filter.value, column.data_type),
    };
  });

  const parsedSorts = sorts.map((sort) => {
    if (!sort.field) {
      throw new Error("Select a field for each sort.");
    }

    return {
      field: sort.field,
      direction: sort.direction,
    };
  });

  const parsedAggregates = aggregates.map((aggregate) => {
    const config = aggregateFunctionOptions.find(
      (item) => item.value === aggregate.function,
    );
    const requiresField = config?.requiresField ?? true;

    if (requiresField && !aggregate.field) {
      throw new Error(`Aggregate ${aggregate.function} requires a field.`);
    }

    return {
      function: aggregate.function,
      field: aggregate.field ? aggregate.field : undefined,
      alias: aggregate.alias.trim() ? aggregate.alias.trim() : undefined,
    };
  });

  return {
    filters: parsedFilters,
    sorts: parsedSorts,
    group_by: groupBy,
    aggregates: parsedAggregates,
    page,
    page_size: pageSize,
  };
}
