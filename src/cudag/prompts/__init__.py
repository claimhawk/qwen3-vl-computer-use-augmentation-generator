# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Derivative works may be released by researchers,
# but original files may not be redistributed or used beyond research purposes.

"""System prompts and tool definitions for computer use training."""

from cudag.prompts.system import (
    CUA_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    get_system_prompt,
)
from cudag.prompts.tools import (
    COMPUTER_USE_TOOL,
    TOOL_ACTIONS,
    ToolCall,
    format_tool_call,
    parse_tool_call,
    validate_tool_call,
)

__all__ = [
    "COMPUTER_USE_TOOL",
    "TOOL_ACTIONS",
    "ToolCall",
    "format_tool_call",
    "parse_tool_call",
    "validate_tool_call",
    "CUA_SYSTEM_PROMPT",
    "SYSTEM_PROMPT",
    "get_system_prompt",
]
