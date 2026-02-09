from __future__ import annotations

from server.agents.models import sanitize_responses_input


def test_sanitize_responses_input_normalizes_assistant_blocks_and_drops_null_id():
    payload = [
        {
            "type": "message",
            "role": "assistant",
            "id": None,
            "content": [
                {"type": "text", "text": "hello"},
                {"type": "reasoning", "summary": "ignore"},
            ],
        }
    ]

    result = sanitize_responses_input(payload)

    assert len(result) == 1
    message = result[0]
    assert message["type"] == "message"
    assert message["role"] == "assistant"
    assert "id" not in message
    assert message["content"] == [
        {"type": "output_text", "text": "hello", "annotations": []}
    ]


def test_sanitize_responses_input_preserves_multimodal_user_blocks():
    payload = [
        {
            "type": "message",
            "role": "user",
            "content": [
                {"type": "text", "text": "analyze this"},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64,AAAA", "detail": "high"},
                },
                {
                    "type": "file",
                    "file": {
                        "file_data": "data:application/pdf;base64,BBBB",
                        "filename": "report.pdf",
                    },
                },
            ],
        }
    ]

    result = sanitize_responses_input(payload)

    assert result == [
        {
            "type": "message",
            "role": "user",
            "content": [
                {"type": "input_text", "text": "analyze this"},
                {
                    "type": "input_image",
                    "image_url": "data:image/png;base64,AAAA",
                    "detail": "high",
                },
                {
                    "type": "input_file",
                    "file_data": "data:application/pdf;base64,BBBB",
                    "filename": "report.pdf",
                },
            ],
        }
    ]


def test_sanitize_responses_input_drops_top_level_reasoning_blocks():
    payload = [
        {"type": "reasoning", "id": None, "content": [{"type": "text", "text": "x"}]},
        {
            "type": "message",
            "role": "user",
            "content": "hi",
        },
    ]

    result = sanitize_responses_input(payload)

    assert result == [{"type": "message", "role": "user", "content": "hi"}]
