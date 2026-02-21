LIST_CONVERSATION_REPORTS_TOOL_DESCRIPTION = """
List archived conversation reports that are enabled for agent retrieval.
Use query to find relevant prior strategy/analysis summaries.
""".strip()

GET_CONVERSATION_REPORT_TOOL_DESCRIPTION = """
Retrieve a specific archived conversation report by report_id.
Only enabled reports are accessible.
""".strip()

CREATE_CONVERSATION_REPORT_TOOL_DESCRIPTION = """
Create an archived conversation report for long-term memory.
Use when the user wants to save a reusable summary for future sessions.
Call this only after the user explicitly confirms saving the report.
""".strip()
