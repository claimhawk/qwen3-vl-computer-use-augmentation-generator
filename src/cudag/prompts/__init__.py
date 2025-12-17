# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""System prompts and tool definitions for computer use training."""

from cudag.prompts.system import (
    CUA_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    get_system_prompt,
)
from cudag.prompts.tools import (
    COMPUTER_USE_TOOL,
    TEXT_VERIFICATION_TOOL,
    TOOL_ACTIONS,
    BboxCall,
    TextVerificationCall,
    ToolCall,
    VerificationRegion,
    format_tool_call,
    parse_tool_call,
    validate_tool_call,
)

__all__ = [
    "COMPUTER_USE_TOOL",
    "TEXT_VERIFICATION_TOOL",
    "TOOL_ACTIONS",
    "BboxCall",
    "TextVerificationCall",
    "ToolCall",
    "VerificationRegion",
    "format_tool_call",
    "parse_tool_call",
    "validate_tool_call",
    "CUA_SYSTEM_PROMPT",
    "SYSTEM_PROMPT",
    "get_system_prompt",
]
