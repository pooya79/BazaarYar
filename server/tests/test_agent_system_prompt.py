from __future__ import annotations

from server.features.agent.prompts.system_prompt import (
    BASE_AGENT_SYSTEM_PROMPT,
    build_agent_system_prompt,
)


def test_prompt_omits_company_context_when_disabled():
    prompt = build_agent_system_prompt(
        company_name="Acme",
        company_description="Desc",
        company_enabled=False,
    )
    assert prompt == BASE_AGENT_SYSTEM_PROMPT


def test_prompt_omits_company_context_when_enabled_but_empty():
    prompt = build_agent_system_prompt(
        company_name="   ",
        company_description="",
        company_enabled=True,
    )
    assert prompt == BASE_AGENT_SYSTEM_PROMPT


def test_prompt_includes_company_context_when_enabled_and_present():
    prompt = build_agent_system_prompt(
        company_name="Acme",
        company_description="We sell shoes.",
        company_enabled=True,
    )
    assert "Company Context" in prompt
    assert "Company name: Acme" in prompt
    assert "Company description: We sell shoes." in prompt
