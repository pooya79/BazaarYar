from __future__ import annotations

from langchain_core.messages import ToolMessage

from server.features.agent.api.formatters import artifact_attachment_ids, format_tool_result


def test_artifact_attachment_ids_extracts_non_empty_values():
    payload = {
        "artifact_attachment_ids": [
            "artifact-1",
            "  artifact-2  ",
            "",
            123,
            None,
        ]
    }

    assert artifact_attachment_ids(payload) == ["artifact-1", "artifact-2"]


def test_format_tool_result_hides_ids_from_formatted_text():
    message = ToolMessage(content="{}", tool_call_id="call-1")
    payload = {
        "status": "succeeded",
        "summary": "Sandbox execution completed.",
        "input_files": [
            {
                "attachment_id": "att-1",
                "original_filename": "campaign.csv",
                "sandbox_filename": "campaign.csv",
                "input_path": "/workspace/input/campaign.csv",
            }
        ],
        "artifacts": [
            {
                "id": "artifact-1",
                "filename": "plot.png",
                "content_type": "image/png",
            }
        ],
    }

    formatted = format_tool_result(message, payload=payload)

    assert "tool_call_id: call-1" in formatted
    assert "input_files:" in formatted
    assert "artifact_attachments:" in formatted
    assert "campaign.csv (original=campaign.csv, path=/workspace/input/campaign.csv)" in formatted
    assert "- plot.png (content_type=image/png)" in formatted
    assert "attachment_id=" not in formatted
    assert "(id=" not in formatted
