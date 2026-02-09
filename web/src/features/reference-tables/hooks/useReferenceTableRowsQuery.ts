import type { MutableRefObject } from "react";
import { useCallback, useEffect, useState } from "react";
import type {
  AggregateDraft,
  FilterDraft,
  SortDraft,
} from "@/features/reference-tables/model/queryDrafts";
import { buildRowsQueryPayload } from "@/features/reference-tables/utils/queryPayload";
import { parseApiErrorMessage } from "@/features/reference-tables/utils/tableUtils";
import { queryTableRows } from "@/shared/api/clients/tables.client";
import type {
  ReferenceTableDetail,
  RowsQueryResponse,
} from "@/shared/api/schemas/tables";

type UseReferenceTableRowsQueryParams = {
  table: ReferenceTableDetail | null;
  isMountedRef: MutableRefObject<boolean>;
};

export function useReferenceTableRowsQuery({
  table,
  isMountedRef,
}: UseReferenceTableRowsQueryParams) {
  const [filters, setFilters] = useState<FilterDraft[]>([]);
  const [sorts, setSorts] = useState<SortDraft[]>([]);
  const [groupBy, setGroupBy] = useState<string[]>([]);
  const [aggregates, setAggregates] = useState<AggregateDraft[]>([]);
  const [pageSize, setPageSize] = useState(50);

  const [queryResult, setQueryResult] = useState<RowsQueryResponse | null>(
    null,
  );
  const [queryError, setQueryError] = useState<string | null>(null);
  const [isQueryLoading, setIsQueryLoading] = useState(false);

  const buildQueryPayload = useCallback(
    (page: number) =>
      buildRowsQueryPayload({
        table,
        filters,
        sorts,
        groupBy,
        aggregates,
        page,
        pageSize,
      }),
    [aggregates, filters, groupBy, pageSize, sorts, table],
  );

  const runQuery = useCallback(
    async (page = 1) => {
      if (!table) {
        return;
      }

      setIsQueryLoading(true);
      setQueryError(null);

      try {
        const payload = buildQueryPayload(page);
        const result = await queryTableRows(table.id, payload);
        if (!isMountedRef.current) {
          return;
        }

        setQueryResult(result);
      } catch (queryLoadError) {
        if (!isMountedRef.current) {
          return;
        }

        setQueryError(
          parseApiErrorMessage(queryLoadError, "Failed to query rows."),
        );
      } finally {
        if (isMountedRef.current) {
          setIsQueryLoading(false);
        }
      }
    },
    [buildQueryPayload, isMountedRef, table],
  );

  useEffect(() => {
    if (!table) {
      setQueryResult(null);
      setQueryError(null);
      return;
    }

    setIsQueryLoading(true);
    setQueryError(null);

    void (async () => {
      try {
        const initialQuery = await queryTableRows(table.id, {
          filters: [],
          sorts: [],
          group_by: [],
          aggregates: [],
          page: 1,
          page_size: pageSize,
        });
        if (!isMountedRef.current) {
          return;
        }
        setQueryResult(initialQuery);
      } catch (queryLoadError) {
        if (!isMountedRef.current) {
          return;
        }
        setQueryError(
          parseApiErrorMessage(queryLoadError, "Failed to query rows."),
        );
      } finally {
        if (isMountedRef.current) {
          setIsQueryLoading(false);
        }
      }
    })();
  }, [isMountedRef, pageSize, table]);

  const resetQuery = useCallback(() => {
    setFilters([]);
    setSorts([]);
    setGroupBy([]);
    setAggregates([]);
    setQueryError(null);
  }, []);

  return {
    filters,
    setFilters,
    sorts,
    setSorts,
    groupBy,
    setGroupBy,
    aggregates,
    setAggregates,
    pageSize,
    setPageSize,
    queryResult,
    queryError,
    setQueryError,
    isQueryLoading,
    buildQueryPayload,
    runQuery,
    resetQuery,
  };
}
