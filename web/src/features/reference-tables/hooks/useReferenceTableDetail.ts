import type { FormEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { parseApiErrorMessage } from "@/features/reference-tables/utils/tableUtils";
import { getTable, updateTable } from "@/shared/api/clients/tables.client";
import type { ReferenceTableDetail } from "@/shared/api/schemas/tables";

type UseReferenceTableDetailParams = {
  tableId: string;
};

export function useReferenceTableDetail({
  tableId,
}: UseReferenceTableDetailParams) {
  const isMountedRef = useRef(true);

  const [table, setTable] = useState<ReferenceTableDetail | null>(null);
  const [isTableLoading, setIsTableLoading] = useState(true);
  const [tableError, setTableError] = useState<string | null>(null);

  const [isEditingMetadata, setIsEditingMetadata] = useState(false);
  const [metadataTitle, setMetadataTitle] = useState("");
  const [metadataDescription, setMetadataDescription] = useState("");
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const [isSavingMetadata, setIsSavingMetadata] = useState(false);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const refreshTableMetadata = useCallback(async () => {
    const detail = await getTable(tableId);
    if (!isMountedRef.current) {
      return;
    }

    setTable(detail);
    setMetadataTitle(detail.title ?? "");
    setMetadataDescription(detail.description ?? "");
  }, [tableId]);

  const loadTable = useCallback(async () => {
    setIsTableLoading(true);
    setTableError(null);

    try {
      await refreshTableMetadata();
    } catch (loadError) {
      if (!isMountedRef.current) {
        return;
      }
      setTableError(parseApiErrorMessage(loadError, "Failed to load table."));
    } finally {
      if (isMountedRef.current) {
        setIsTableLoading(false);
      }
    }
  }, [refreshTableMetadata]);

  useEffect(() => {
    void loadTable();
  }, [loadTable]);

  const saveMetadata = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!table) {
        return;
      }

      const nextTitle = metadataTitle.trim();
      const nextDescription = metadataDescription.trim();

      const payload: {
        title?: string;
        description?: string;
      } = {};

      if (nextTitle && nextTitle !== (table.title ?? "")) {
        payload.title = nextTitle;
      }
      if (nextDescription && nextDescription !== (table.description ?? "")) {
        payload.description = nextDescription;
      }

      if (Object.keys(payload).length === 0) {
        setIsEditingMetadata(false);
        return;
      }

      setIsSavingMetadata(true);
      setMetadataError(null);
      try {
        const updated = await updateTable(table.id, payload);
        if (!isMountedRef.current) {
          return;
        }

        setTable(updated);
        setMetadataTitle(updated.title ?? "");
        setMetadataDescription(updated.description ?? "");
        setIsEditingMetadata(false);
      } catch (saveError) {
        if (!isMountedRef.current) {
          return;
        }

        setMetadataError(
          parseApiErrorMessage(saveError, "Failed to update table metadata."),
        );
      } finally {
        if (isMountedRef.current) {
          setIsSavingMetadata(false);
        }
      }
    },
    [metadataDescription, metadataTitle, table],
  );

  const cancelMetadataEdit = useCallback(() => {
    setIsEditingMetadata(false);
    setMetadataTitle(table?.title ?? "");
    setMetadataDescription(table?.description ?? "");
    setMetadataError(null);
  }, [table?.description, table?.title]);

  return {
    isMountedRef,
    table,
    isTableLoading,
    tableError,
    loadTable,
    refreshTableMetadata,
    isEditingMetadata,
    setIsEditingMetadata,
    metadataTitle,
    setMetadataTitle,
    metadataDescription,
    setMetadataDescription,
    metadataError,
    isSavingMetadata,
    saveMetadata,
    cancelMetadataEdit,
  };
}
