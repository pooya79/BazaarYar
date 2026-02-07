import { z } from "zod";

export const tableDataTypeSchema = z.enum([
  "text",
  "integer",
  "float",
  "boolean",
  "date",
  "timestamp",
  "json",
]);

export const sortDirectionSchema = z.enum(["asc", "desc"]);

export const filterOperatorSchema = z.enum([
  "eq",
  "neq",
  "gt",
  "gte",
  "lt",
  "lte",
  "in",
  "contains",
  "starts_with",
  "ends_with",
  "is_null",
  "not_null",
]);

export const aggregateFunctionSchema = z.enum([
  "count",
  "sum",
  "avg",
  "min",
  "max",
]);

export const importStatusSchema = z.enum([
  "pending",
  "running",
  "completed",
  "failed",
]);

export const exportFormatSchema = z.enum(["csv", "json", "xlsx"]);

export const sourceActorSchema = z.enum(["user", "agent", "import"]);

export const importFormatSchema = z.enum(["csv", "json", "xlsx"]);

export const referenceTableColumnInputSchema = z.object({
  name: z.string().min(1).max(63),
  data_type: tableDataTypeSchema,
  nullable: z.boolean().default(true),
  description: z.string().max(1024).nullable().optional(),
  semantic_hint: z.string().max(128).nullable().optional(),
  constraints_json: z.record(z.string(), z.unknown()).nullable().optional(),
  default_value: z.unknown().nullable().optional(),
});

export const referenceTableCreateInputSchema = z.object({
  name: z.string().min(1).max(63),
  title: z.string().max(255).nullable().optional(),
  description: z.string().max(2048).nullable().optional(),
  columns: z.array(referenceTableColumnInputSchema).min(1),
});

export const referenceTableUpdateInputSchema = z.object({
  title: z.string().max(255).nullable().optional(),
  description: z.string().max(2048).nullable().optional(),
  columns: z.array(referenceTableColumnInputSchema).nullable().optional(),
});

export const referenceTableColumnSchema = z.object({
  id: z.string(),
  name: z.string(),
  position: z.number().int().nonnegative(),
  data_type: tableDataTypeSchema,
  nullable: z.boolean(),
  description: z.string().nullable().optional(),
  semantic_hint: z.string().nullable().optional(),
  constraints_json: z.record(z.string(), z.unknown()).nullable().optional(),
  default_value: z.unknown().nullable().optional(),
});

export const referenceTableSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  title: z.string().nullable().optional(),
  description: z.string().nullable().optional(),
  row_count: z.number().int().nonnegative(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const referenceTableDetailSchema = referenceTableSummarySchema.extend({
  columns: z.array(referenceTableColumnSchema),
});

export const queryFilterSchema = z.object({
  field: z.string().min(1).max(63),
  op: filterOperatorSchema,
  value: z.unknown().nullable().optional(),
});

export const querySortSchema = z.object({
  field: z.string().min(1).max(63),
  direction: sortDirectionSchema.default("asc"),
});

export const queryAggregateSchema = z.object({
  function: aggregateFunctionSchema,
  field: z.string().max(63).nullable().optional(),
  alias: z.string().max(63).nullable().optional(),
});

export const rowsQueryInputSchema = z.object({
  filters: z.array(queryFilterSchema).default([]),
  sorts: z.array(querySortSchema).default([]),
  page: z.number().int().min(1).default(1),
  page_size: z.number().int().min(1).max(500).default(50),
  group_by: z.array(z.string()).default([]),
  aggregates: z.array(queryAggregateSchema).default([]),
});

export const queriedRowSchema = z.object({
  id: z.string(),
  version: z.number().int().nonnegative(),
  values_json: z.record(z.string(), z.unknown()),
  created_at: z.string(),
  updated_at: z.string(),
});

export const rowsQueryResponseSchema = z.object({
  total_rows: z.number().int().nonnegative(),
  page: z.number().int().min(1),
  page_size: z.number().int().min(1),
  rows: z.array(queriedRowSchema),
  aggregate_row: z.record(z.string(), z.unknown()).nullable().optional(),
  grouped_rows: z.array(z.record(z.string(), z.unknown())).default([]),
  provenance: z.record(z.string(), z.unknown()),
});

export const rowUpsertSchema = z.object({
  row_id: z.string().nullable().optional(),
  values_json: z.record(z.string(), z.unknown()),
  source_actor: sourceActorSchema.default("user"),
  source_ref: z.string().max(255).nullable().optional(),
});

export const rowsBatchInputSchema = z
  .object({
    upserts: z.array(rowUpsertSchema).default([]),
    delete_row_ids: z.array(z.string()).default([]),
  })
  .superRefine((value, ctx) => {
    if (value.upserts.length === 0 && value.delete_row_ids.length === 0) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Provide at least one upsert or delete operation.",
        path: ["upserts"],
      });
    }
  });

export const rowsBatchResultSchema = z.object({
  inserted: z.number().int().nonnegative(),
  updated: z.number().int().nonnegative(),
  deleted: z.number().int().nonnegative(),
});

export const importStartInputSchema = z.object({
  attachment_id: z.string(),
  source_format: importFormatSchema.nullable().optional(),
  has_header: z.boolean().default(true),
  delimiter: z.string().nullable().optional(),
  column_overrides: z.record(z.string(), tableDataTypeSchema).default({}),
});

export const importJobSummarySchema = z.object({
  id: z.string(),
  table_id: z.string(),
  status: importStatusSchema,
  source_filename: z.string().nullable().optional(),
  source_format: importFormatSchema.nullable().optional(),
  total_rows: z.number().int().nonnegative(),
  inserted_rows: z.number().int().nonnegative(),
  updated_rows: z.number().int().nonnegative(),
  deleted_rows: z.number().int().nonnegative(),
  error_count: z.number().int().nonnegative(),
  errors_json: z.array(z.record(z.string(), z.unknown())),
  created_at: z.string(),
  started_at: z.string().nullable().optional(),
  finished_at: z.string().nullable().optional(),
  inferred_columns: z
    .array(z.record(z.string(), z.unknown()))
    .nullable()
    .optional(),
  provenance: z.record(z.string(), z.unknown()).nullable().optional(),
});

export const exportInputSchema = z.object({
  format: exportFormatSchema,
  query: rowsQueryInputSchema.nullable().optional(),
  include_header: z.boolean().default(true),
});

export type TableDataType = z.infer<typeof tableDataTypeSchema>;
export type SortDirection = z.infer<typeof sortDirectionSchema>;
export type FilterOperator = z.infer<typeof filterOperatorSchema>;
export type AggregateFunction = z.infer<typeof aggregateFunctionSchema>;
export type ImportStatus = z.infer<typeof importStatusSchema>;
export type ExportFormat = z.infer<typeof exportFormatSchema>;
export type ImportFormat = z.infer<typeof importFormatSchema>;

export type ReferenceTableColumnInput = z.infer<
  typeof referenceTableColumnInputSchema
>;
export type ReferenceTableCreateInput = z.infer<
  typeof referenceTableCreateInputSchema
>;
export type ReferenceTableUpdateInput = z.infer<
  typeof referenceTableUpdateInputSchema
>;
export type ReferenceTableColumn = z.infer<typeof referenceTableColumnSchema>;
export type ReferenceTableSummary = z.infer<typeof referenceTableSummarySchema>;
export type ReferenceTableDetail = z.infer<typeof referenceTableDetailSchema>;
export type QueryFilter = z.infer<typeof queryFilterSchema>;
export type QuerySort = z.infer<typeof querySortSchema>;
export type QueryAggregate = z.infer<typeof queryAggregateSchema>;
export type RowsQueryInput = z.infer<typeof rowsQueryInputSchema>;
export type QueriedRow = z.infer<typeof queriedRowSchema>;
export type RowsQueryResponse = z.infer<typeof rowsQueryResponseSchema>;
export type RowUpsert = z.infer<typeof rowUpsertSchema>;
export type RowsBatchInput = z.infer<typeof rowsBatchInputSchema>;
export type RowsBatchResult = z.infer<typeof rowsBatchResultSchema>;
export type ImportStartInput = z.infer<typeof importStartInputSchema>;
export type ImportJobSummary = z.infer<typeof importJobSummarySchema>;
export type ExportInput = z.infer<typeof exportInputSchema>;
