# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Computer use tool definition and tool_call formatting.

This module codifies the canonical tool_call format used in VLM training datasets.
All tool calls must use this format for consistency across generators.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal

# Valid actions for computer_use tool
TOOL_ACTIONS = Literal[
    "key",
    "type",
    "mouse_move",
    "left_click",
    "left_click_drag",
    "right_click",
    "middle_click",
    "double_click",
    "triple_click",
    "scroll",
    "hscroll",
    "wait",
    "terminate",
    "answer",
]

# Action descriptions for system prompt
ACTION_DESCRIPTIONS = {
    "key": "Press keys in order, release in reverse.",
    "type": "Type a string of text.",
    "mouse_move": "Move the cursor to (x, y).",
    "left_click": "Left click at (x, y).",
    "left_click_drag": "Click and drag from current to (x, y).",
    "right_click": "Right click at (x, y).",
    "middle_click": "Middle click at (x, y).",
    "double_click": "Double-click at (x, y).",
    "triple_click": "Triple-click at (x, y) (simulated as double-click).",
    "scroll": "Scroll the mouse wheel.",
    "hscroll": "Horizontal scroll.",
    "wait": "Wait N seconds.",
    "terminate": "End the task with a status.",
    "answer": "Answer a question.",
}

# Actions that require coordinate parameter
COORDINATE_ACTIONS = {
    "mouse_move",
    "left_click",
    "left_click_drag",
    "right_click",
    "middle_click",
    "double_click",
    "triple_click",
    "scroll",
    "hscroll",
}

# Actions that require specific parameters
ACTION_REQUIRED_PARAMS: dict[str, list[str]] = {
    "key": ["keys"],
    "type": ["text"],
    "scroll": ["coordinate", "pixels"],
    "hscroll": ["coordinate", "pixels"],
    "wait": ["time"],
    "terminate": ["status"],
}

# Canonical computer_use tool definition (JSON schema)
COMPUTER_USE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name_for_human": "computer_use",
        "name": "computer_use",
        "description": "Perform computer actions",
        "parameters": {
            "properties": {
                "action": {
                    "description": "\n".join(
                        f"* `{action}`: {desc}" for action, desc in ACTION_DESCRIPTIONS.items()
                    ),
                    "enum": list(ACTION_DESCRIPTIONS.keys()),
                    "type": "string",
                },
                "keys": {
                    "description": "Required only by `action=key`.",
                    "type": "array",
                },
                "text": {
                    "description": "Required only by `action=type`.",
                    "type": "string",
                },
                "coordinate": {
                    "description": "Mouse coordinates (1000x1000 normalized).",
                    "type": "array",
                },
                "pixels": {
                    "description": "The amount of scrolling.",
                    "type": "number",
                },
                "time": {
                    "description": "The seconds to wait.",
                    "type": "number",
                },
                "status": {
                    "description": "The status of the task.",
                    "type": "string",
                    "enum": ["success", "failure"],
                },
            },
            "required": ["action"],
            "type": "object",
        },
        "args_format": "Format the arguments as a JSON object.",
    },
}

# Text verification tool definition (JSON schema)
TEXT_VERIFICATION_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name_for_human": "text_verification",
        "name": "text_verification",
        "description": "Request OCR verification of text in two screen regions",
        "parameters": {
            "properties": {
                "regions": {
                    "description": "Array of exactly 2 regions to compare",
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "bbox_2d": {
                                "description": "Bounding box [x1, y1, x2, y2] in RU (0-1000)",
                                "type": "array",
                                "items": {"type": "number"},
                                "minItems": 4,
                                "maxItems": 4,
                            },
                            "label": {
                                "description": "Human-readable label for the region",
                                "type": "string",
                            },
                        },
                        "required": ["bbox_2d", "label"],
                    },
                    "minItems": 2,
                    "maxItems": 2,
                },
            },
            "required": ["regions"],
            "type": "object",
        },
        "args_format": "Format the arguments as a JSON object.",
    },
}


@dataclass
class BboxCall:
    """Represents a get_bbox tool call for element grounding.

    This is the canonical format for bounding box detection in VLMGen datasets.
    Used for "grounding" task types that identify element locations.
    """

    bbox_2d: tuple[int, int, int, int]
    """Bounding box coordinates [x1, y1, x2, y2] in RU (0-1000)."""

    label: str | None = None
    """Optional human-readable label of the element being located."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        args: dict[str, Any] = {"bbox_2d": list(self.bbox_2d)}
        if self.label:
            args["label"] = self.label
        return {
            "name": "get_bbox",
            "arguments": args,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BboxCall:
        """Create from dictionary."""
        if data.get("name") != "get_bbox":
            raise ValueError(f"Expected get_bbox tool, got: {data.get('name')}")

        args = data.get("arguments", {})
        bbox = args.get("bbox_2d", [0, 0, 0, 0])

        return cls(
            bbox_2d=tuple(bbox),  # type: ignore[arg-type]
            label=args.get("label"),
        )

    @classmethod
    def create(
        cls, bbox_2d: tuple[int, int, int, int], label: str | None = None
    ) -> BboxCall:
        """Create a get_bbox tool call.

        Args:
            bbox_2d: Bounding box [x1, y1, x2, y2] in RU units (0-1000)
            label: Optional human-readable label of the element (e.g., "Appts")

        Returns:
            BboxCall instance
        """
        return cls(bbox_2d=bbox_2d, label=label)


@dataclass
class VerificationRegion:
    """A region for text verification."""

    bbox_2d: tuple[int, int, int, int]
    """Bounding box coordinates [x1, y1, x2, y2] in RU (0-1000)."""

    label: str
    """Human-readable label for the region (e.g., 'codes_1', 'prov_2')."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"bbox_2d": list(self.bbox_2d), "label": self.label}


@dataclass
class TextVerificationCall:
    """Represents a text_verification tool call.

    Used for comparing text content between two screen regions.
    The agent harness crops both regions, runs OCR, and compares.

    Example output:
        <tool_call>
        {"name": "text_verification", "arguments": {"regions": [
            {"bbox_2d": [280, 265, 305, 430], "label": "codes_1"},
            {"bbox_2d": [460, 542, 485, 595], "label": "codes_2"}
        ]}}
        </tool_call>
    """

    regions: tuple[VerificationRegion, VerificationRegion]
    """Exactly two regions to compare."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": "text_verification",
            "arguments": {"regions": [r.to_dict() for r in self.regions]},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TextVerificationCall:
        """Create from dictionary."""
        if data.get("name") != "text_verification":
            raise ValueError(f"Expected text_verification tool, got: {data.get('name')}")

        args = data.get("arguments", {})
        regions_data = args.get("regions", [])

        if len(regions_data) != 2:
            raise ValueError(f"Expected exactly 2 regions, got: {len(regions_data)}")

        regions = tuple(
            VerificationRegion(
                bbox_2d=tuple(r["bbox_2d"]),  # type: ignore[arg-type]
                label=r["label"],
            )
            for r in regions_data
        )

        return cls(regions=regions)  # type: ignore[arg-type]

    @classmethod
    def create(
        cls,
        region1: tuple[tuple[int, int, int, int], str],
        region2: tuple[tuple[int, int, int, int], str],
    ) -> TextVerificationCall:
        """Create a text verification call.

        Args:
            region1: (bbox_2d, label) for first region
            region2: (bbox_2d, label) for second region

        Returns:
            TextVerificationCall instance
        """
        return cls(
            regions=(
                VerificationRegion(bbox_2d=region1[0], label=region1[1]),
                VerificationRegion(bbox_2d=region2[0], label=region2[1]),
            )
        )


@dataclass
class ToolCall:
    """Represents a computer_use tool call.

    This is the canonical format for all tool calls in VLMGen datasets.
    """

    action: str
    coordinate: tuple[int, int] | None = None
    pixels: int | None = None
    keys: list[str] | None = None
    text: str | None = None
    time: float | None = None
    status: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        args: dict[str, Any] = {"action": self.action}

        if self.coordinate is not None:
            args["coordinate"] = list(self.coordinate)
        if self.pixels is not None:
            args["pixels"] = self.pixels
        if self.keys is not None:
            args["keys"] = self.keys
        if self.text is not None:
            args["text"] = self.text
        if self.time is not None:
            args["time"] = self.time
        if self.status is not None:
            args["status"] = self.status

        # Include any extra fields
        args.update(self.extra)

        return {"name": "computer_use", "arguments": args}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCall:
        """Create from dictionary."""
        if data.get("name") != "computer_use":
            raise ValueError(f"Expected computer_use tool, got: {data.get('name')}")

        args = data.get("arguments", {})
        coord = args.get("coordinate")

        # Extract known fields
        known_fields = {"action", "coordinate", "pixels", "keys", "text", "time", "status"}
        extra = {k: v for k, v in args.items() if k not in known_fields}

        return cls(
            action=args["action"],
            coordinate=tuple(coord) if coord else None,
            pixels=args.get("pixels"),
            keys=args.get("keys"),
            text=args.get("text"),
            time=args.get("time"),
            status=args.get("status"),
            extra=extra,
        )

    @classmethod
    def left_click(cls, coordinate: tuple[int, int]) -> ToolCall:
        """Create a left_click tool call."""
        return cls(action="left_click", coordinate=coordinate)

    @classmethod
    def double_click(cls, coordinate: tuple[int, int]) -> ToolCall:
        """Create a double_click tool call."""
        return cls(action="double_click", coordinate=coordinate)

    @classmethod
    def right_click(cls, coordinate: tuple[int, int]) -> ToolCall:
        """Create a right_click tool call."""
        return cls(action="right_click", coordinate=coordinate)

    @classmethod
    def scroll(cls, coordinate: tuple[int, int], pixels: int) -> ToolCall:
        """Create a scroll tool call. Negative pixels = scroll up."""
        return cls(action="scroll", coordinate=coordinate, pixels=pixels)

    @classmethod
    def key_press(cls, keys: list[str]) -> ToolCall:
        """Create a key press tool call."""
        return cls(action="key", keys=keys)

    @classmethod
    def type_text(cls, text: str) -> ToolCall:
        """Create a type tool call."""
        return cls(action="type", text=text)

    @classmethod
    def wait(cls, seconds: float) -> ToolCall:
        """Create a wait tool call."""
        return cls(action="wait", time=seconds)

    @classmethod
    def terminate(cls, status: str = "success") -> ToolCall:
        """Create a terminate tool call."""
        return cls(action="terminate", status=status)


def format_tool_call(
    tool_call: ToolCall | BboxCall | TextVerificationCall | dict[str, Any],
) -> str:
    """Format a tool call as XML-wrapped JSON string.

    This is the canonical output format for GPT responses in training data.

    Args:
        tool_call: ToolCall, BboxCall, TextVerificationCall, or dict with {name, arguments}

    Returns:
        Formatted string like:
        <tool_call>
        {"name": "computer_use", "arguments": {...}}
        </tool_call>

        or for bounding box:
        <tool_call>
        {"name": "get_bbox", "arguments": {"label": "...", "bbox_2d": [...]}}
        </tool_call>

        or for text verification:
        <tool_call>
        {"name": "text_verification", "arguments": {"regions": [...]}}
        </tool_call>
    """
    if isinstance(tool_call, (ToolCall, BboxCall, TextVerificationCall)):
        data = tool_call.to_dict()
    else:
        data = tool_call

    json_str = json.dumps(data)
    return f"<tool_call>\n{json_str}\n</tool_call>"


# Regex pattern for parsing tool calls
TOOL_CALL_PATTERN = re.compile(
    r"<tool_call>\s*(?P<json>\{.*?\})\s*</tool_call>",
    re.DOTALL | re.IGNORECASE,
)


def parse_tool_call(text: str) -> ToolCall | None:
    """Parse a tool call from model output text.

    Args:
        text: Model output containing <tool_call>...</tool_call>

    Returns:
        Parsed ToolCall or None if not found
    """
    match = TOOL_CALL_PATTERN.search(text)
    if not match:
        return None

    try:
        data = json.loads(match.group("json"))
        return ToolCall.from_dict(data)
    except (json.JSONDecodeError, ValueError, KeyError):
        return None


def validate_tool_call(tool_call: ToolCall) -> list[str]:
    """Validate a tool call and return list of errors.

    Args:
        tool_call: ToolCall to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    # Check action is valid
    if tool_call.action not in ACTION_DESCRIPTIONS:
        errors.append(f"Invalid action: {tool_call.action}")
        return errors  # Can't validate further without valid action

    # Check coordinate is provided for coordinate-requiring actions
    if tool_call.action in COORDINATE_ACTIONS and tool_call.coordinate is None:
        errors.append(f"Action '{tool_call.action}' requires coordinate")

    # Check coordinate values are in valid range
    if tool_call.coordinate is not None:
        x, y = tool_call.coordinate
        if not (0 <= x <= 1000 and 0 <= y <= 1000):
            errors.append(f"Coordinate out of range [0, 1000]: ({x}, {y})")

    # Check required parameters
    required = ACTION_REQUIRED_PARAMS.get(tool_call.action, [])
    for param in required:
        value = getattr(tool_call, param, None)
        if value is None:
            errors.append(f"Action '{tool_call.action}' requires '{param}'")

    # Validate scroll pixels
    if tool_call.action in ("scroll", "hscroll") and tool_call.pixels is not None:
        if not isinstance(tool_call.pixels, (int, float)):
            errors.append(f"Invalid pixels value: {tool_call.pixels}")

    # Validate terminate status
    if tool_call.action == "terminate" and tool_call.status is not None:
        if tool_call.status not in ("success", "failure"):
            errors.append(f"Invalid terminate status: {tool_call.status}")

    return errors
