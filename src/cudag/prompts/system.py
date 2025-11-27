# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Derivative works may be released by researchers,
# but original files may not be redistributed or used beyond research purposes.

"""System prompts for VLM training datasets.

These prompts define the tool interface presented to the model during training.
Projects can use built-in prompts or provide custom ones.
"""

from __future__ import annotations

import json
from typing import Literal

from cudag.prompts.tools import ACTION_DESCRIPTIONS, COMPUTER_USE_TOOL

# OSWorld-style verbose system prompt (used by calendar)
# fmt: off
SYSTEM_PROMPT_OSWORLD = """Use a mouse and keyboard to interact with a computer, and take screenshots.
* This is an interface to a desktop GUI. You do not have access to a terminal or applications menu. You must click on desktop icons to start applications.
* Some applications may take time to start or process actions, so you may need to wait and take successive screenshots to see the results of your actions. E.g. if you click on Firefox and a window doesn't open, try wait and taking another screenshot.
* The screen's resolution is 1000x1000.
* Whenever you intend to move the cursor to click on an element like an icon, you should consult a screenshot to determine the coordinates of the element before moving the cursor.
* If you tried clicking on a program or link but it failed to load even after waiting, try adjusting your cursor position so that the tip of the cursor visually falls on the element that you want to click.
* Make sure to click any buttons, links, icons, etc with the cursor tip in the center of the element. Don't click boxes on their edges unless asked.

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{
  "name": "computer_use",
  "description": "Perform computer actions",
  "parameters": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "enum": ["key", "type", "mouse_move", "left_click", "left_click_drag", "right_click", "middle_click", "double_click", "triple_click", "scroll", "hscroll", "wait", "terminate", "answer"]
      },
      "coordinate": {
        "type": "array",
        "items": {"type": "integer"},
        "description": "X and Y coordinates in 1000x1000 normalized space"
      }
    },
    "required": ["action"]
  }
}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>

# Action descriptions

""" + "\n".join(f"* `{action}`: {desc}" for action, desc in ACTION_DESCRIPTIONS.items()) + """

# Response format

Response format for every step:
1) Action: a short imperative describing what to do in the UI.
2) A single <tool_call>...</tool_call> block containing only the JSON.

Rules:
- Output exactly in the order: Action, <tool_call>.
- Be brief: one sentence for Action.
- Do not output anything else outside those parts.
- If finishing, use action=terminate in the tool call."""
# fmt: on


def _build_compact_prompt() -> str:
    """Build the compact system prompt dynamically."""
    tools_json = json.dumps(COMPUTER_USE_TOOL, indent="\t")
    return f"""# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{tools_json}
</tools>

For each function call, return a json object with function name and arguments within
<tool_call></tool_call> XML tags:
<tool_call>
{{"name": <function-name>, "arguments": <args-json-object>}}
</tool_call>

# Response format

Response format for every step:
1) Action: a short imperative describing what to do in the UI.
2) A single <tool_call>...</tool_call> block containing only the JSON:
\t{{"name": <function-name>, "arguments": <args-json-object>}}.

Rules:
- Output exactly in the order: Action, <tool_call>.
- Be brief: one sentence for Action.
- Do not output anything else outside those parts.
- If finishing, use action=terminate in the tool call."""


# Compact system prompt (used by claim-window)
SYSTEM_PROMPT_COMPACT = _build_compact_prompt()

# Available prompt styles
PROMPT_STYLES = {
    "osworld": SYSTEM_PROMPT_OSWORLD,
    "compact": SYSTEM_PROMPT_COMPACT,
}

PromptStyle = Literal["osworld", "compact"]


def get_system_prompt(style: PromptStyle | str = "compact") -> str:
    """Get a system prompt by style name.

    Args:
        style: Prompt style name or "osworld" or "compact"

    Returns:
        System prompt string

    Raises:
        ValueError: If style is not recognized
    """
    if style in PROMPT_STYLES:
        return PROMPT_STYLES[style]

    raise ValueError(f"Unknown prompt style: {style}. Available: {list(PROMPT_STYLES.keys())}")
