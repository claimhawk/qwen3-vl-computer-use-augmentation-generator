# Request from Root Agent - text_verification Feature

**Date:** 2025-12-17
**Priority:** P0 - Foundation for other work
**Type:** Feature Implementation

---

## Summary

Implement the `text_verification` tool call infrastructure in CUDAG. This is agent-harness-aware grounding that enables OCR-based text comparison between two screen regions.

---

## Context

See full research and plan:
- Research: `/Users/michaeloneal/development/claimhawk/.claude/research/text-verification-tool.md`
- Plan: `/Users/michaeloneal/development/claimhawk/.claude/plans/text-verification-plan.md`

---

## Your Tasks

### Task 1: Add TextVerificationCall to tools.py

**File:** `src/cudag/prompts/tools.py`

Add after `BboxCall` class:

```python
@dataclass
class VerificationRegion:
    """A region for text verification."""
    bbox_2d: tuple[int, int, int, int]
    label: str

    def to_dict(self) -> dict[str, Any]:
        return {"bbox_2d": list(self.bbox_2d), "label": self.label}


@dataclass
class TextVerificationCall:
    """Represents a text_verification tool call.
    
    Used for comparing text content between two screen regions.
    The agent harness crops both regions, runs OCR, and compares.
    """
    regions: tuple[VerificationRegion, VerificationRegion]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": "text_verification",
            "arguments": {
                "regions": [r.to_dict() for r in self.regions]
            }
        }

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
        """
        return cls(regions=(
            VerificationRegion(bbox_2d=region1[0], label=region1[1]),
            VerificationRegion(bbox_2d=region2[0], label=region2[1]),
        ))
```

Add the tool schema constant:

```python
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
                                "maxItems": 4
                            },
                            "label": {
                                "description": "Human-readable label for the region",
                                "type": "string"
                            }
                        },
                        "required": ["bbox_2d", "label"]
                    },
                    "minItems": 2,
                    "maxItems": 2
                }
            },
            "required": ["regions"],
            "type": "object"
        },
        "args_format": "Format the arguments as a JSON object."
    }
}
```

Update `format_tool_call()` to handle `TextVerificationCall`.

### Task 2: Create verification_task.py

**File:** `src/cudag/core/verification_task.py` (NEW)

Create base class for verification tasks:

```python
"""Base verification task for text comparison between regions.

Example output:
    <tool_call>
    {"name": "text_verification", "arguments": {"regions": [
        {"bbox_2d": [280, 265, 305, 430], "label": "codes_1"},
        {"bbox_2d": [460, 542, 485, 595], "label": "codes_2"}
    ]}}
    </tool_call>
"""

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from cudag.core.task import BaseTask, TaskContext, TaskSample, TestCase
from cudag.prompts.tools import TextVerificationCall, format_tool_call

if TYPE_CHECKING:
    from PIL import Image


class VerificationTaskBase(BaseTask):
    """Base class for text verification tasks."""
    
    task_type: str = "text_verification"
    
    PROMPT_TEMPLATES = [
        "Verify that the text in {region1} matches the text in {region2}",
        "Compare the {region1} with {region2} to check if they match",
        "Check if {region1} and {region2} contain the same value",
    ]
    
    @abstractmethod
    def get_verification_pairs(self) -> list[tuple[dict, dict, bool]]:
        """Return verification pairs.
        
        Returns:
            List of (region1_def, region2_def, expected_match) tuples.
            Each region_def has: bbox_2d, label
        """
        pass
    
    @abstractmethod
    def render_image(self, ctx: TaskContext) -> tuple[Any, dict[str, Any]]:
        """Render an image for verification."""
        pass
    
    # ... implement generate_sample() and generate_test()
```

### Task 3: Export from package

Update `src/cudag/__init__.py` and `src/cudag/core/__init__.py` to export:
- `TextVerificationCall`
- `VerificationRegion`
- `TEXT_VERIFICATION_TOOL`
- `VerificationTaskBase`

### Task 4: Add unit tests

**File:** `tests/test_tools.py`

Add tests for:
- TextVerificationCall creation and serialization
- format_tool_call() with TextVerificationCall
- Round-trip parse/format

---

## Acceptance Criteria

1. `TextVerificationCall.create((bbox1, "label1"), (bbox2, "label2"))` works
2. `format_tool_call(verification_call)` produces valid XML-wrapped JSON
3. `TEXT_VERIFICATION_TOOL` matches the system prompt format
4. `VerificationTaskBase` can be subclassed by generators
5. All tests pass

---

## Downstream Dependencies

After you complete this:
- system-prompt agent will add tool to SYSTEM_PROMPT.txt
- claim-window-generator will implement VerificationTask
- oracle-agent will implement runtime handler

Please notify root-agent when complete.
