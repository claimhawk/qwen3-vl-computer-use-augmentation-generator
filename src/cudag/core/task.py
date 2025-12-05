# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Base task class and data structures for VLM training samples.

Tasks are the "Controller" in VLMGen's Screen/State/Renderer/Task architecture.
Each task type (click-day, scroll-grid, etc.) defines:
- How to generate prompts
- What tool calls are expected
- How to create state for rendering
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from random import Random
from typing import TYPE_CHECKING, Any

from cudag.prompts.tools import ToolCall, format_tool_call

if TYPE_CHECKING:
    from cudag.core.dataset import DatasetConfig
    from cudag.core.renderer import BaseRenderer


@dataclass
class TaskSample:
    """Output of a task generation.

    This represents a single training sample in the dataset.
    """

    id: str
    """Unique identifier for this sample."""

    image_path: Path
    """Path to the generated image file."""

    human_prompt: str
    """The human instruction (without <image> prefix)."""

    tool_call: ToolCall
    """The expected tool call response."""

    pixel_coords: tuple[int, int]
    """Pixel coordinates of the target (for real_coords in metadata)."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Task-specific metadata (task_type is added automatically)."""

    image_size: tuple[int, int] = (1000, 1000)
    """Size of the generated image (width, height)."""


@dataclass
class TestCase:
    """Output of test case generation.

    This represents a single test case for evaluating model accuracy.
    """

    test_id: str
    """Unique identifier for this test case."""

    screenshot: Path
    """Path to the test screenshot."""

    prompt: str
    """The human instruction (without <image> prefix)."""

    expected_action: dict[str, Any]
    """Expected tool call as dict (for JSON serialization)."""

    tolerance: tuple[int, int] | int
    """Allowed coordinate tolerance (x, y) in RU units."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Test-specific metadata."""

    pixel_coords: tuple[int, int] | None = None
    """Original pixel coordinates (before normalization)."""


@dataclass
class TaskContext:
    """Context passed to task generation methods.

    Provides access to shared resources like RNG, output directories, and config.
    """

    rng: Random
    """Seeded random number generator for reproducibility."""

    index: int
    """Current sample index (for ID generation)."""

    output_dir: Path
    """Directory for generated images."""

    config: dict[str, Any]
    """Task-specific configuration."""

    dataset_name: str
    """Name prefix for generated IDs."""


class BaseTask(ABC):
    """Abstract base class for task types.

    Subclass this to create new task types. Each task type defines:
    - task_type: Unique identifier (e.g., "click-day", "scroll-grid")
    - generate_samples(): How to generate training samples from one image (1:N)
    - generate_tests(): How to generate test cases from one image (1:N)

    The key insight is that one rendered image can produce MULTIPLE training
    samples. For example, a claim window image can have:
    - "Click the procedure code" → one coordinate
    - "Click the fee column" → different coordinate
    - "Scroll down in the grid" → scroll action

    Example:
        class ClaimWindowTask(BaseTask):
            task_type = "claim-window"

            def generate_samples(self, ctx: TaskContext) -> list[TaskSample]:
                # 1. Generate state and render ONCE
                state = ClaimWindowState.generate(ctx.rng)
                image, metadata = self.renderer.render(state)
                image_path = self.save_image(image, ctx)

                # 2. Derive MULTIPLE samples from this one image
                samples = []

                # Sample 1: Click procedure code
                samples.append(TaskSample(
                    id=self.build_id(ctx, "_click_code"),
                    image_path=image_path,
                    human_prompt="Click the procedure code",
                    tool_call=ToolCall.left_click(code_coords),
                    pixel_coords=code_coords,
                    ...
                ))

                # Sample 2: Click fee
                samples.append(TaskSample(
                    id=self.build_id(ctx, "_click_fee"),
                    image_path=image_path,  # SAME IMAGE
                    human_prompt="Click the fee column",
                    tool_call=ToolCall.left_click(fee_coords),
                    pixel_coords=fee_coords,
                    ...
                ))

                return samples
    """

    task_type: str
    """Unique identifier for this task type (e.g., 'click-day', 'scroll-grid')."""

    def __init__(
        self, config: DatasetConfig | dict[str, Any], renderer: BaseRenderer[Any]
    ) -> None:
        """Initialize the task.

        Args:
            config: Task-specific configuration from generator.yaml (DatasetConfig or dict)
            renderer: Renderer instance for generating images
        """
        self.config = config
        self.renderer = renderer

    def generate_samples(self, ctx: TaskContext) -> list[TaskSample]:
        """Generate training samples from one rendered image.

        Override this to generate multiple samples from a single render.
        Default implementation calls generate_sample() once for backwards compat.

        Args:
            ctx: Task context with RNG, index, output directory, etc.

        Returns:
            List of TaskSample objects (can share the same image_path).
        """
        return [self.generate_sample(ctx)]

    @abstractmethod
    def generate_sample(self, ctx: TaskContext) -> TaskSample:
        """Generate one training sample.

        For simple 1:1 image-to-sample tasks, implement this.
        For 1:N image-to-samples, override generate_samples() instead.

        Args:
            ctx: Task context with RNG, index, output directory, etc.

        Returns:
            TaskSample with all required fields populated.
        """
        pass

    def generate_tests(self, ctx: TaskContext) -> list[TestCase]:
        """Generate test cases from one rendered image.

        Override this to generate multiple tests from a single render.
        Default implementation calls generate_test() once for backwards compat.

        Args:
            ctx: Task context with RNG, index, output directory, etc.

        Returns:
            List of TestCase objects (can share the same screenshot).
        """
        return [self.generate_test(ctx)]

    @abstractmethod
    def generate_test(self, ctx: TaskContext) -> TestCase:
        """Generate one test case.

        For simple 1:1 image-to-test tasks, implement this.
        For 1:N image-to-tests, override generate_tests() instead.

        Args:
            ctx: Task context with RNG, index, output directory, etc.

        Returns:
            TestCase with all required fields populated.
        """
        pass

    def format_gpt_response(self, tool_call: ToolCall) -> str:
        """Format the GPT response for this sample.

        Override this to customize the response format (e.g., add <think> tags).

        Args:
            tool_call: The tool call to format

        Returns:
            Formatted string for the "gpt" conversation turn
        """
        return format_tool_call(tool_call)

    def save_image(
        self,
        image: Any,  # PIL.Image.Image
        ctx: TaskContext,
        extension: str = "jpg",
        quality: int = 85,
        prefix: str | None = None,
    ) -> Path:
        """Save a generated image to the output directory.

        Args:
            image: PIL Image to save
            ctx: Task context
            extension: Image format (default: jpg)
            quality: JPEG quality (ignored for PNG)
            prefix: Optional prefix for filename (e.g., "eval" for eval images)

        Returns:
            Path to saved image
        """
        images_dir = ctx.output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        if prefix:
            filename = f"{prefix}_{ctx.index:05d}.{extension}"
        else:
            filename = f"{ctx.dataset_name}_{ctx.index:05d}.{extension}"
        path = images_dir / filename

        if extension.lower() in ("jpg", "jpeg"):
            image.save(path, quality=quality)
        else:
            image.save(path)

        return path

    def build_id(self, ctx: TaskContext, suffix: str = "") -> str:
        """Build a sample ID from context.

        Args:
            ctx: Task context
            suffix: Optional suffix to add (e.g., "_task")

        Returns:
            Formatted ID string
        """
        base = f"{ctx.dataset_name}_{ctx.index:05d}"
        return f"{base}{suffix}" if suffix else base
