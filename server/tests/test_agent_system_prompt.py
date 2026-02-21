from __future__ import annotations

from server.features.agent.prompts.system_prompt import (
    BASE_AGENT_SYSTEM_PROMPT,
    PYTHON_ENABLED_SYSTEM_PROMPT_APPENDIX,
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


def test_prompt_includes_python_appendix_when_enabled():
    prompt = build_agent_system_prompt(
        company_name="",
        company_description="",
        company_enabled=False,
        python_code_enabled=True,
    )
    assert PYTHON_ENABLED_SYSTEM_PROMPT_APPENDIX in prompt
    assert "Python Code Runner Guidance" in prompt
    assert "sandbox_mount_ready_files" in prompt
    assert "input_files" in prompt
    assert "use only filenames listed in the runtime context" not in prompt


def test_prompt_omits_python_appendix_when_disabled():
    prompt = build_agent_system_prompt(
        company_name="Acme",
        company_description="We sell shoes.",
        company_enabled=True,
        python_code_enabled=False,
    )
    assert PYTHON_ENABLED_SYSTEM_PROMPT_APPENDIX not in prompt
    assert "Python Code Runner Guidance" not in prompt


def test_prompt_includes_company_context_and_python_appendix_when_both_enabled():
    prompt = build_agent_system_prompt(
        company_name="Acme",
        company_description="We sell shoes.",
        company_enabled=True,
        python_code_enabled=True,
    )
    assert "Company Context" in prompt
    assert "Company name: Acme" in prompt
    assert "Company description: We sell shoes." in prompt
    assert PYTHON_ENABLED_SYSTEM_PROMPT_APPENDIX in prompt
    assert "Python Code Runner Guidance" in prompt


def test_base_prompt_omits_tool_usage_instructions():
    assert "When helpful, call tools to retrieve facts or compute results." not in BASE_AGENT_SYSTEM_PROMPT
    assert "run_python_code" not in BASE_AGENT_SYSTEM_PROMPT
    assert "create_conversation_report" not in BASE_AGENT_SYSTEM_PROMPT
    assert "load_dataframe(path, **kwargs)" not in BASE_AGENT_SYSTEM_PROMPT
    assert "input_filenames" not in BASE_AGENT_SYSTEM_PROMPT
    assert "attachment_ids" not in BASE_AGENT_SYSTEM_PROMPT
    assert "pass attachment_ids as a list of selected user attachment IDs" not in BASE_AGENT_SYSTEM_PROMPT
