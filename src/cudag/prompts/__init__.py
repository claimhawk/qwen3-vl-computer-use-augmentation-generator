# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Derivative works may be released by researchers,
# but original files may not be redistributed or used beyond research purposes.

"""System prompts and tool definitions for computer use training."""

from cudag.prompts.system import (
    SYSTEM_PROMPT_COMPACT,
    SYSTEM_PROMPT_OSWORLD,
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
    "SYSTEM_PROMPT_OSWORLD",
    "SYSTEM_PROMPT_COMPACT",
    "get_system_prompt",
]
