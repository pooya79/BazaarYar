BASE_AGENT_SYSTEM_PROMPT = (
    "You are BazaarYar, an assistant that is concise, practical, and transparent. "
    "When helpful, call tools to retrieve facts or compute results. "
    "Expose tool usage and provide a brief reasoning summary when the user requests it. "
    "For run_python_code: the sandbox mounts all attachments from the current conversation automatically. "
    "When writing Python, choose files from AVAILABLE_FILES and use load_dataframe(name). "
)


def build_agent_system_prompt(
    *,
    company_name: str,
    company_description: str,
    company_enabled: bool,
) -> str:
    if not company_enabled:
        return BASE_AGENT_SYSTEM_PROMPT

    name = company_name.strip()
    description = company_description.strip()
    if not name and not description:
        return BASE_AGENT_SYSTEM_PROMPT

    parts = [BASE_AGENT_SYSTEM_PROMPT, "\n\nCompany Context:\n"]
    if name:
        parts.append(f"Company name: {name}\n")
    if description:
        parts.append(f"Company description: {description}\n")
    parts.append(
        "Treat this context as authoritative brand background unless the user explicitly corrects it."
    )
    return "".join(parts)
