import type { ReferenceTableDetail } from "@/lib/api/schemas/tables";
import { formatCellValue } from "@/view/referenceTables/utils";
import { panelClass } from "./constants";

type ColumnsSectionProps = {
  table: ReferenceTableDetail;
};

export function ColumnsSection({ table }: ColumnsSectionProps) {
  return (
    <div className={panelClass}>
      <h3 className="text-base font-semibold text-marketing-text-primary">
        Column definitions
      </h3>
      <div className="mt-3 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-marketing-border text-marketing-text-muted">
              <th className="px-2 py-2 font-semibold">Name</th>
              <th className="px-2 py-2 font-semibold">Type</th>
              <th className="px-2 py-2 font-semibold">Nullable</th>
              <th className="px-2 py-2 font-semibold">Default</th>
              <th className="px-2 py-2 font-semibold">Description</th>
            </tr>
          </thead>
          <tbody>
            {table.columns
              .slice()
              .sort((a, b) => a.position - b.position)
              .map((column) => (
                <tr
                  key={column.id}
                  className="border-b border-marketing-border/70 last:border-none"
                >
                  <td className="px-2 py-2 font-medium text-marketing-text-primary">
                    {column.name}
                  </td>
                  <td className="px-2 py-2 text-marketing-text-secondary">
                    {column.data_type}
                  </td>
                  <td className="px-2 py-2 text-marketing-text-secondary">
                    {column.nullable ? "Yes" : "No"}
                  </td>
                  <td className="px-2 py-2 text-marketing-text-secondary">
                    {formatCellValue(column.default_value)}
                  </td>
                  <td className="px-2 py-2 text-marketing-text-secondary">
                    {column.description || "-"}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
