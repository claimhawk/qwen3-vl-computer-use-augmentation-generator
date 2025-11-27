# Copyright (c) 2025 Tylt LLC. All rights reserved.
"""Tests for prompts/tools.py ToolCall and formatting."""

import pytest

from cudag.prompts.tools import (
    COMPUTER_USE_TOOL,
    ToolCall,
    format_tool_call,
    parse_tool_call,
    validate_tool_call,
)


class TestToolCall:
    """Tests for ToolCall dataclass."""

    def test_left_click(self) -> None:
        tc = ToolCall.left_click((500, 300))
        assert tc.action == "left_click"
        assert tc.coordinate == (500, 300)

    def test_scroll(self) -> None:
        tc = ToolCall.scroll((400, 200), 300)
        assert tc.action == "scroll"
        assert tc.coordinate == (400, 200)
        assert tc.pixels == 300

    def test_scroll_negative(self) -> None:
        tc = ToolCall.scroll((400, 200), -300)
        assert tc.pixels == -300

    def test_key_press(self) -> None:
        tc = ToolCall.key_press(["ctrl", "c"])
        assert tc.action == "key"
        assert tc.keys == ["ctrl", "c"]

    def test_type_text(self) -> None:
        tc = ToolCall.type_text("Hello World")
        assert tc.action == "type"
        assert tc.text == "Hello World"

    def test_wait(self) -> None:
        tc = ToolCall.wait(2.5)
        assert tc.action == "wait"
        assert tc.time == 2.5

    def test_terminate_success(self) -> None:
        tc = ToolCall.terminate("success")
        assert tc.action == "terminate"
        assert tc.status == "success"

    def test_terminate_failure(self) -> None:
        tc = ToolCall.terminate("failure")
        assert tc.status == "failure"

    def test_to_dict(self) -> None:
        tc = ToolCall.left_click((500, 300))
        d = tc.to_dict()
        assert d["name"] == "computer_use"
        assert d["arguments"]["action"] == "left_click"
        assert d["arguments"]["coordinate"] == [500, 300]

    def test_to_dict_scroll(self) -> None:
        tc = ToolCall.scroll((400, 200), 300)
        d = tc.to_dict()
        assert d["arguments"]["pixels"] == 300

    def test_to_dict_excludes_none(self) -> None:
        tc = ToolCall.left_click((100, 100))
        d = tc.to_dict()
        assert "pixels" not in d["arguments"]
        assert "keys" not in d["arguments"]
        assert "text" not in d["arguments"]

    def test_from_dict(self) -> None:
        data = {
            "name": "computer_use",
            "arguments": {
                "action": "left_click",
                "coordinate": [500, 300],
            },
        }
        tc = ToolCall.from_dict(data)
        assert tc.action == "left_click"
        assert tc.coordinate == (500, 300)

    def test_from_dict_scroll(self) -> None:
        data = {
            "name": "computer_use",
            "arguments": {
                "action": "scroll",
                "coordinate": [400, 200],
                "pixels": 300,
            },
        }
        tc = ToolCall.from_dict(data)
        assert tc.action == "scroll"
        assert tc.pixels == 300

    def test_from_dict_wrong_tool_raises(self) -> None:
        data = {"name": "wrong_tool", "arguments": {"action": "click"}}
        with pytest.raises(ValueError, match="Expected computer_use"):
            ToolCall.from_dict(data)

    def test_roundtrip(self) -> None:
        original = ToolCall.scroll((577, 300), -300)
        d = original.to_dict()
        restored = ToolCall.from_dict(d)
        assert restored.action == original.action
        assert restored.coordinate == original.coordinate
        assert restored.pixels == original.pixels


class TestFormatToolCall:
    """Tests for format_tool_call function."""

    def test_format_basic(self) -> None:
        tc = ToolCall.left_click((500, 300))
        result = format_tool_call(tc)
        assert "<tool_call>" in result
        assert "</tool_call>" in result
        assert '"action": "left_click"' in result
        assert '"coordinate": [500, 300]' in result

    def test_format_from_dict(self) -> None:
        d = {"name": "computer_use", "arguments": {"action": "wait", "time": 1.0}}
        result = format_tool_call(d)
        assert "<tool_call>" in result
        assert '"action": "wait"' in result

    def test_format_scroll(self) -> None:
        tc = ToolCall.scroll((400, 200), 300)
        result = format_tool_call(tc)
        assert '"pixels": 300' in result


class TestParseToolCall:
    """Tests for parse_tool_call function."""

    def test_parse_valid(self) -> None:
        text = """
<tool_call>
{"name": "computer_use", "arguments": {"action": "left_click", "coordinate": [500, 300]}}
</tool_call>
"""
        tc = parse_tool_call(text)
        assert tc is not None
        assert tc.action == "left_click"
        assert tc.coordinate == (500, 300)

    def test_parse_with_surrounding_text(self) -> None:
        text = """I will click on the button.
<tool_call>
{"name": "computer_use", "arguments": {"action": "left_click", "coordinate": [100, 200]}}
</tool_call>
Done."""
        tc = parse_tool_call(text)
        assert tc is not None
        assert tc.action == "left_click"

    def test_parse_no_tool_call(self) -> None:
        text = "Just some text without a tool call."
        tc = parse_tool_call(text)
        assert tc is None

    def test_parse_invalid_json(self) -> None:
        text = "<tool_call>not valid json</tool_call>"
        tc = parse_tool_call(text)
        assert tc is None

    def test_parse_case_insensitive(self) -> None:
        text = '<TOOL_CALL>{"name": "computer_use", "arguments": {"action": "wait", "time": 1}}</TOOL_CALL>'
        tc = parse_tool_call(text)
        assert tc is not None
        assert tc.action == "wait"


class TestValidateToolCall:
    """Tests for validate_tool_call function."""

    def test_validate_valid_click(self) -> None:
        tc = ToolCall.left_click((500, 300))
        errors = validate_tool_call(tc)
        assert errors == []

    def test_validate_valid_scroll(self) -> None:
        tc = ToolCall.scroll((400, 200), 300)
        errors = validate_tool_call(tc)
        assert errors == []

    def test_validate_invalid_action(self) -> None:
        tc = ToolCall(action="invalid_action")
        errors = validate_tool_call(tc)
        assert len(errors) == 1
        assert "Invalid action" in errors[0]

    def test_validate_missing_coordinate(self) -> None:
        tc = ToolCall(action="left_click")  # No coordinate
        errors = validate_tool_call(tc)
        assert any("requires coordinate" in e for e in errors)

    def test_validate_coordinate_out_of_range(self) -> None:
        tc = ToolCall(action="left_click", coordinate=(1500, 500))
        errors = validate_tool_call(tc)
        assert any("out of range" in e for e in errors)

    def test_validate_negative_coordinate(self) -> None:
        tc = ToolCall(action="left_click", coordinate=(-10, 500))
        errors = validate_tool_call(tc)
        assert any("out of range" in e for e in errors)

    def test_validate_missing_pixels(self) -> None:
        tc = ToolCall(action="scroll", coordinate=(500, 300))  # No pixels
        errors = validate_tool_call(tc)
        assert any("requires 'pixels'" in e for e in errors)

    def test_validate_missing_keys(self) -> None:
        tc = ToolCall(action="key")  # No keys
        errors = validate_tool_call(tc)
        assert any("requires 'keys'" in e for e in errors)

    def test_validate_invalid_terminate_status(self) -> None:
        tc = ToolCall(action="terminate", status="maybe")
        errors = validate_tool_call(tc)
        assert any("Invalid terminate status" in e for e in errors)

    def test_validate_valid_terminate(self) -> None:
        tc = ToolCall.terminate("success")
        errors = validate_tool_call(tc)
        assert errors == []


class TestComputerUseTool:
    """Tests for COMPUTER_USE_TOOL definition."""

    def test_tool_has_required_fields(self) -> None:
        assert COMPUTER_USE_TOOL["type"] == "function"
        assert "function" in COMPUTER_USE_TOOL

    def test_function_definition(self) -> None:
        func = COMPUTER_USE_TOOL["function"]
        assert func["name"] == "computer_use"
        assert "parameters" in func

    def test_parameters_schema(self) -> None:
        params = COMPUTER_USE_TOOL["function"]["parameters"]
        assert params["type"] == "object"
        assert "action" in params["properties"]
        assert "coordinate" in params["properties"]
        assert "pixels" in params["properties"]

    def test_action_enum(self) -> None:
        action_prop = COMPUTER_USE_TOOL["function"]["parameters"]["properties"]["action"]
        assert "enum" in action_prop
        assert "left_click" in action_prop["enum"]
        assert "scroll" in action_prop["enum"]
        assert "key" in action_prop["enum"]
        assert "type" in action_prop["enum"]
