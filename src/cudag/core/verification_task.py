# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Base verification task for text comparison between regions.

Verification tasks train the model to request OCR comparison between
two screen regions. The agent harness (not the model) performs the
actual OCR and comparison.

Example output:
    <tool_call>
    {"name": "text_verification", "arguments": {"regions": [
        {"bbox_2d": [280, 265, 305, 430], "label": "codes_1"},
        {"bbox_2d": [460, 542, 485, 595], "label": "codes_2"}
    ]}}
    </tool_call>
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cudag.core.task import BaseTask, TaskContext, TaskSample, TestCase
from cudag.prompts.tools import TextVerificationCall, format_tool_call

if TYPE_CHECKING:
    from PIL import Image


@dataclass
class VerificationPair:
    """Defines a pair of regions to verify.

    Attributes:
        region1_bbox: First region bounding box [x1, y1, x2, y2] in RU (0-1000)
        region1_label: Human-readable label for first region
        region2_bbox: Second region bounding box [x1, y1, x2, y2] in RU (0-1000)
        region2_label: Human-readable label for second region
        expected_match: Whether the regions should contain matching text
    """

    region1_bbox: tuple[int, int, int, int]
    region1_label: str
    region2_bbox: tuple[int, int, int, int]
    region2_label: str
    expected_match: bool = True


@dataclass
class VerificationSample(TaskSample):
    """Extended TaskSample for verification tasks.

    Adds verification-specific fields to the base TaskSample.
    """

    verification_call: TextVerificationCall | None = None
    """The verification tool call (alternative to tool_call)."""

    expected_match: bool = True
    """Whether the regions are expected to match."""


@dataclass
class VerificationTestCase(TestCase):
    """Extended TestCase for verification tasks."""

    expected_match: bool = True
    """Whether the regions should contain matching text."""

    region1_label: str = ""
    """Label for the first region."""

    region2_label: str = ""
    """Label for the second region."""


class VerificationTaskBase(BaseTask):
    """Base class for text verification tasks.

    Subclass this to create verification tasks that train the model
    to request OCR comparison between screen regions.

    The model learns to:
    1. Identify which regions need comparison
    2. Output the text_verification tool call with correct bboxes
    3. The agent harness handles actual OCR and comparison

    Example:
        class ClaimCodeVerificationTask(VerificationTaskBase):
            task_type = "verify-codes"

            PROMPT_TEMPLATES = [
                "Verify that {region1} matches {region2}",
                "Check if the code in {region1} equals {region2}",
            ]

            def get_verification_pairs(self, ctx: TaskContext) -> list[VerificationPair]:
                # Return pairs of regions to compare
                return [
                    VerificationPair(
                        region1_bbox=(280, 265, 305, 430),
                        region1_label="procedure_code",
                        region2_bbox=(460, 542, 485, 595),
                        region2_label="line_code",
                        expected_match=True,
                    )
                ]

            def render_verification_image(
                self, ctx: TaskContext
            ) -> tuple[Image, dict[str, Any]]:
                # Render image with verification regions
                state = self.generate_state(ctx)
                return self.renderer.render(state)
    """

    task_type: str = "text_verification"
    """Override in subclass with specific verification task name."""

    PROMPT_TEMPLATES: list[str] = [
        "Verify that the text in {region1} matches the text in {region2}",
        "Compare {region1} with {region2} to check if they contain the same value",
        "Check if {region1} and {region2} have matching text",
        "Confirm that {region1} equals {region2}",
    ]
    """Prompt templates with {region1} and {region2} placeholders."""

    @abstractmethod
    def get_verification_pairs(self, ctx: TaskContext) -> list[VerificationPair]:
        """Return verification pairs for this image.

        Override this to define which regions should be compared.

        Args:
            ctx: Task context with RNG, index, etc.

        Returns:
            List of VerificationPair objects defining regions to compare.
        """
        pass

    @abstractmethod
    def render_verification_image(
        self, ctx: TaskContext
    ) -> tuple[Any, dict[str, Any]]:
        """Render an image for verification.

        Override this to generate the screen image.

        Args:
            ctx: Task context

        Returns:
            Tuple of (PIL Image, metadata dict)
        """
        pass

    def generate_prompt(
        self, pair: VerificationPair, ctx: TaskContext
    ) -> str:
        """Generate a human prompt for the verification pair.

        Args:
            pair: The verification pair
            ctx: Task context with RNG

        Returns:
            Human-readable prompt string
        """
        template = ctx.rng.choice(self.PROMPT_TEMPLATES)
        return template.format(
            region1=pair.region1_label,
            region2=pair.region2_label,
        )

    def generate_sample(self, ctx: TaskContext) -> TaskSample:
        """Generate a single verification sample.

        For 1:1 image-to-sample, override generate_samples() for 1:N.
        """
        samples = self.generate_samples(ctx)
        return samples[0] if samples else self._empty_sample(ctx)

    def generate_samples(self, ctx: TaskContext) -> list[TaskSample]:
        """Generate verification samples from one rendered image.

        One image can produce multiple verification samples if there
        are multiple pairs to compare.
        """
        # Render image once
        image, metadata = self.render_verification_image(ctx)
        image_path = self.save_image(image, ctx)

        # Get verification pairs
        pairs = self.get_verification_pairs(ctx)

        samples: list[TaskSample] = []
        for i, pair in enumerate(pairs):
            # Create verification tool call
            verification_call = TextVerificationCall.create(
                region1=(pair.region1_bbox, pair.region1_label),
                region2=(pair.region2_bbox, pair.region2_label),
            )

            # Generate prompt
            prompt = self.generate_prompt(pair, ctx)

            # Build sample
            suffix = f"_verify_{i}" if len(pairs) > 1 else "_verify"
            sample = TaskSample(
                id=self.build_id(ctx, suffix),
                image_path=image_path,
                human_prompt=prompt,
                tool_call=verification_call,  # type: ignore[arg-type]
                pixel_coords=(0, 0),  # Not applicable for verification
                metadata={
                    "task_type": self.task_type,
                    "expected_match": pair.expected_match,
                    "region1_label": pair.region1_label,
                    "region2_label": pair.region2_label,
                    **metadata,
                },
            )
            samples.append(sample)

        return samples

    def generate_test(self, ctx: TaskContext) -> TestCase:
        """Generate a single verification test case."""
        tests = self.generate_tests(ctx)
        return tests[0] if tests else self._empty_test(ctx)

    def generate_tests(self, ctx: TaskContext) -> list[TestCase]:
        """Generate verification test cases from one rendered image."""
        # Render image once
        image, metadata = self.render_verification_image(ctx)
        image_path = self.save_image(image, ctx, prefix="test")

        # Get verification pairs
        pairs = self.get_verification_pairs(ctx)

        tests: list[TestCase] = []
        for i, pair in enumerate(pairs):
            # Create verification tool call
            verification_call = TextVerificationCall.create(
                region1=(pair.region1_bbox, pair.region1_label),
                region2=(pair.region2_bbox, pair.region2_label),
            )

            # Generate prompt
            prompt = self.generate_prompt(pair, ctx)

            # Build test case
            suffix = f"_verify_{i}" if len(pairs) > 1 else "_verify"
            test = VerificationTestCase(
                test_id=self.build_id(ctx, suffix),
                screenshot=image_path,
                prompt=prompt,
                expected_action=verification_call.to_dict(),
                tolerance=0,  # Exact bbox match required
                expected_match=pair.expected_match,
                region1_label=pair.region1_label,
                region2_label=pair.region2_label,
                metadata={
                    "task_type": self.task_type,
                    **metadata,
                },
            )
            tests.append(test)

        return tests

    def format_gpt_response(self, tool_call: Any) -> str:
        """Format the GPT response for verification samples."""
        return format_tool_call(tool_call)

    def _empty_sample(self, ctx: TaskContext) -> TaskSample:
        """Return empty sample when no pairs available."""
        from cudag.prompts.tools import ToolCall as TC

        return TaskSample(
            id=self.build_id(ctx, "_empty"),
            image_path=Path("/dev/null"),
            human_prompt="",
            tool_call=TC.terminate("failure"),
            pixel_coords=(0, 0),
        )

    def _empty_test(self, ctx: TaskContext) -> TestCase:
        """Return empty test when no pairs available."""
        from cudag.prompts.tools import ToolCall as TC

        return TestCase(
            test_id=self.build_id(ctx, "_empty"),
            screenshot=Path("/dev/null"),
            prompt="",
            expected_action=TC.terminate("failure").to_dict(),
            tolerance=0,
        )
