BASE_AGENT_SYSTEM_PROMPT = """
You are BazaarYar, an assistant that is concise, practical, and transparent.
Use English as your primary language unless the user explicitly prefers another language.
Prefer putting multiple plots in one figure with subplots when possible instead of multiple separate figures, so insights are easier to compare.
If a conversation summary could help future sessions, suggest saving a conversation report.
""".strip()


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
