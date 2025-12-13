# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Base grounding task for element bounding box detection.

This module provides a base task class for generating "grounding" training data,
where the model must identify the bounding box of a specified element.

Example output:
    <tool_call>
    {"name": "get_bbox", "arguments": {"element": "search button", "bbox_2d": [123, 456, 789, 1011]}}
    </tool_call>
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from cudag.annotation import AnnotatedElement, AnnotationConfig
from cudag.core.task import BaseTask, TaskContext, TaskSample, TestCase
from cudag.prompts.tools import BboxCall, format_tool_call

if TYPE_CHECKING:
    from random import Random

    from PIL import Image


def bbox_to_ru(
    bbox: tuple[int, int, int, int],
    image_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    """Convert bbox (x, y, width, height) to RU coordinates [x1, y1, x2, y2].

    Args:
        bbox: Bounding box as (x, y, width, height) in pixels
        image_size: Image size as (width, height) in pixels

    Returns:
        Bounding box as (x1, y1, x2, y2) in RU units (0-1000)
    """
    x, y, w, h = bbox
    img_w, img_h = image_size

    x1 = int((x / img_w) * 1000)
    y1 = int((y / img_h) * 1000)
    x2 = int(((x + w) / img_w) * 1000)
    y2 = int(((y + h) / img_h) * 1000)

    return (x1, y1, x2, y2)


def scale_bbox(
    bbox: tuple[int, int, int, int],
    scale_x: float,
    scale_y: float,
) -> tuple[int, int, int, int]:
    """Scale a bounding box by given factors.

    Args:
        bbox: Bounding box as (x, y, width, height)
        scale_x: X scale factor
        scale_y: Y scale factor

    Returns:
        Scaled bounding box
    """
    x, y, w, h = bbox
    return (int(x * scale_x), int(y * scale_y), int(w * scale_x), int(h * scale_y))


class GroundingTaskBase(BaseTask):
    """Base class for grounding tasks that identify element bounding boxes.

    Subclasses must implement:
        - get_annotation_config(): Return the annotation config
        - get_image_scale(): Return (scale_x, scale_y) for coordinate scaling
        - render_image(ctx): Render an image and return (image, metadata)

    The task will:
        1. Pick a random element from the annotation
        2. Generate a prompt like "Locate the {element_label}"
        3. Return a BboxCall with the element's bounding box in RU coordinates
    """

    task_type: str = "grounding"

    # Prompt templates that can be customized by subclasses
    PROMPT_TEMPLATES = [
        "Locate the {element}",
        "Find the bounding box of the {element}",
        "Where is the {element}?",
        "Identify the {element} region",
    ]

    @abstractmethod
    def get_annotation_config(self) -> AnnotationConfig:
        """Return the annotation config for this generator."""
        pass

    @abstractmethod
    def get_image_scale(self) -> tuple[float, float]:
        """Return (scale_x, scale_y) for coordinate scaling.

        If annotation was made at different size than generator output,
        return the scale factors to convert annotation coords to output coords.
        """
        pass

    @abstractmethod
    def render_image(self, ctx: TaskContext) -> tuple[Any, dict[str, Any]]:
        """Render an image for this task.

        Args:
            ctx: Task context with RNG, index, etc.

        Returns:
            Tuple of (PIL.Image, metadata dict)
        """
        pass

    def get_groundable_elements(self) -> list[AnnotatedElement]:
        """Get elements that can be used for grounding.

        Override this to filter which elements are included in grounding tasks.
        By default, returns all elements with non-empty labels.

        Returns:
            List of elements to use for grounding
        """
        config = self.get_annotation_config()
        return [el for el in config.elements if el.label]

    def get_prompt(self, element: AnnotatedElement, rng: Random) -> str:
        """Generate a prompt for the given element.

        Override this to customize prompt generation.

        Args:
            element: The element to generate a prompt for
            rng: Random number generator

        Returns:
            Prompt string
        """
        template = rng.choice(self.PROMPT_TEMPLATES)
        return template.format(element=element.label)

    def generate_sample(self, ctx: TaskContext) -> TaskSample:
        """Generate a grounding training sample."""
        # Render the image
        image, metadata = self.render_image(ctx)
        image_path = self.save_image(image, ctx)

        # Pick a random element
        elements = self.get_groundable_elements()
        element = ctx.rng.choice(elements)

        # Scale the bbox to generator output size
        scale_x, scale_y = self.get_image_scale()
        scaled_bbox = scale_bbox(element.bbox, scale_x, scale_y)

        # Convert to RU coordinates [x1, y1, x2, y2]
        bbox_ru = bbox_to_ru(scaled_bbox, image.size)

        # Create the prompt
        prompt = self.get_prompt(element, ctx.rng)

        # Create BboxCall
        bbox_call = BboxCall.create(element=element.label, bbox_2d=bbox_ru)

        # Center point for metadata (midpoint of bbox)
        center_x = scaled_bbox[0] + scaled_bbox[2] // 2
        center_y = scaled_bbox[1] + scaled_bbox[3] // 2

        return TaskSample(
            id=self.build_id(ctx),
            image_path=image_path,
            human_prompt=prompt,
            tool_call=bbox_call,  # type: ignore[arg-type]
            pixel_coords=(center_x, center_y),
            metadata={
                "task_type": self.task_type,
                "element_label": element.label,
                "element_type": element.element_type,
                "bbox_pixels": list(scaled_bbox),
                "bbox_ru": list(bbox_ru),
                **metadata,
            },
            image_size=image.size,
        )

    def generate_test(self, ctx: TaskContext) -> TestCase:
        """Generate a grounding test case."""
        # Render the image
        image, metadata = self.render_image(ctx)
        image_path = self.save_image(image, ctx, prefix="test")

        # Pick a random element
        elements = self.get_groundable_elements()
        element = ctx.rng.choice(elements)

        # Scale the bbox to generator output size
        scale_x, scale_y = self.get_image_scale()
        scaled_bbox = scale_bbox(element.bbox, scale_x, scale_y)

        # Convert to RU coordinates [x1, y1, x2, y2]
        bbox_ru = bbox_to_ru(scaled_bbox, image.size)

        # Create the prompt
        prompt = self.get_prompt(element, ctx.rng)

        # Create expected action as dict
        expected_action = {
            "name": "get_bbox",
            "arguments": {
                "element": element.label,
                "bbox_2d": list(bbox_ru),
            },
        }

        # Center point for metadata
        center_x = scaled_bbox[0] + scaled_bbox[2] // 2
        center_y = scaled_bbox[1] + scaled_bbox[3] // 2

        return TestCase(
            test_id=f"test_{ctx.index:04d}",
            screenshot=image_path,
            prompt=prompt,
            expected_action=expected_action,
            tolerance=(50, 50),  # Generous tolerance for bbox matching
            metadata={
                "task_type": self.task_type,
                "element_label": element.label,
                "element_type": element.element_type,
                "bbox_pixels": list(scaled_bbox),
                "image_size": image.size,
                **metadata,
            },
            pixel_coords=(center_x, center_y),
        )

    def format_gpt_response(self, tool_call: BboxCall) -> str:  # type: ignore[override]
        """Format the GPT response for this sample."""
        return format_tool_call(tool_call)
