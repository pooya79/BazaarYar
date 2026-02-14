LIST_TABLES_TOOL_DESCRIPTION = "List available reference tables and core metadata."
DESCRIBE_TABLE_TOOL_DESCRIPTION = "Describe a reference table including schema and metadata."
QUERY_TABLE_TOOL_DESCRIPTION = (
    "Run a safe query against a reference table. Provide query_json with keys: "
    "filters, sorts, page, page_size, group_by, aggregates."
)
MUTATE_TABLE_TOOL_DESCRIPTION = (
    "Mutate table rows with upserts/deletes. Provide batch_json with keys upserts/delete_row_ids. "
    "Writes are allowed only when TABLES_AGENT_WRITE_ENABLED is true."
)
