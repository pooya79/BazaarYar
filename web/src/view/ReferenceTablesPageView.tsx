"use client";

import { useRef, useState } from "react";
import type {
  ReferenceTable,
  ReferenceTableAction,
} from "@/view/ReferenceTablesView";
import {
  initialReferenceTables,
  ReferenceTablesView,
} from "@/view/ReferenceTablesView";

export function ReferenceTablesPageView() {
  const [referenceTables, setReferenceTables] = useState<ReferenceTable[]>(
    initialReferenceTables,
  );
  const [tableMenuOpenId, setTableMenuOpenId] = useState<string | null>(null);
  const referenceTableCounter = useRef(1);

  const handleAddReferenceTable = () => {
    const nextIndex = referenceTableCounter.current++;
    const nextTable: ReferenceTable = {
      id: `reference-${Date.now()}-${nextIndex}`,
      name: `Reference Table ${nextIndex}`,
      description: "Define approved values agents should rely on.",
      rows: 0,
      columns: 4,
      source: "Manual entry",
      refresh: "On demand",
      updatedAt: "Just now",
      status: "active",
      assignedAgents: [],
      tags: ["draft"],
    };
    setReferenceTables((prev) => [nextTable, ...prev]);
  };

  const handleReferenceTableAction = (
    action: ReferenceTableAction,
    tableId: string,
  ) => {
    if (action === "toggle") {
      setReferenceTables((prev) =>
        prev.map((table) =>
          table.id === tableId
            ? {
                ...table,
                status: table.status === "active" ? "disabled" : "active",
              }
            : table,
        ),
      );
      setTableMenuOpenId(null);
      return;
    }

    if (action === "remove") {
      setReferenceTables((prev) =>
        prev.map((table) =>
          table.id === tableId ? { ...table, assignedAgents: [] } : table,
        ),
      );
      setTableMenuOpenId(null);
      return;
    }

    if (action === "delete") {
      setReferenceTables((prev) =>
        prev.filter((table) => table.id !== tableId),
      );
      setTableMenuOpenId(null);
    }
  };

  return (
    <ReferenceTablesView
      tables={referenceTables}
      tableMenuOpenId={tableMenuOpenId}
      onTableMenuOpenChange={setTableMenuOpenId}
      onAddTable={handleAddReferenceTable}
      onTableAction={handleReferenceTableAction}
    />
  );
}
