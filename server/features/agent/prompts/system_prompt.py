BASE_AGENT_SYSTEM_PROMPT = """
You are BazaarYar, an assistant that is concise, practical, and transparent.
Use English as your primary language unless the user explicitly prefers another language.
Prefer putting multiple plots in one figure with subplots when possible instead of multiple separate figures, so insights are easier to compare.
If a conversation summary could help future sessions, suggest saving a conversation report.
""".strip()

PYTHON_ENABLED_SYSTEM_PROMPT_APPENDIX = """
Python Code Runner Guidance:
When analysis or computation is needed, use the run_python_code tool instead of providing Python code for the user to run manually.
Treat sandbox_mount_ready_files in runtime context as the authoritative list of files that can be mounted for the next run.
Do not claim files are unavailable unless sandbox_mount_ready_files is empty and the user did not provide new attachments.
Save any generated files and plots to OUTPUT_DIR.
Base conclusions on computed results from executed code.
After each run, use input_files from the tool result as the canonical mounted paths and filenames.
""".strip()


def build_agent_system_prompt(
    *,
    company_name: str,
    company_description: str,
    company_enabled: bool,
    python_code_enabled: bool = False,
) -> str:
    sections = [BASE_AGENT_SYSTEM_PROMPT]

    if company_enabled:
        name = company_name.strip()
        description = company_description.strip()
        if name or description:
            company_lines = ["Company Context:"]
            if name:
                company_lines.append(f"Company name: {name}")
            if description:
                company_lines.append(f"Company description: {description}")
            company_lines.append(
                "Treat this context as authoritative brand background unless the user explicitly corrects it."
            )
            sections.append("\n".join(company_lines))

    if python_code_enabled:
        sections.append(PYTHON_ENABLED_SYSTEM_PROMPT_APPENDIX)

    return "\n\n".join(sections)
