from app.providers.llm.gemini import _tool_names


def test_tool_names_maps_id_to_function_name():
    messages = [
        {"role": "user", "content": "hi"},
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "gem-0-request_test_drive",
                    "name": "request_test_drive",
                    "input": {},
                }
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "gem-0-request_test_drive",
                    "content": "ok",
                }
            ],
        },
    ]
    assert _tool_names(messages)["gem-0-request_test_drive"] == "request_test_drive"


def test_tool_names_empty_for_plain_text():
    assert _tool_names([{"role": "user", "content": "hello"}]) == {}
