# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Base class for iconlist element tasks.

This module provides an abstract base class for tasks that target iconlist
elements in annotation.json. When a task targets an iconlist, it generates
one sample per icon in that list.

Element type determines generation behavior:
- iconlist -> generate one sample per icon
- button -> generate one sample (not handled here)
- loading -> handled separately by wait tasks
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from random import Random
from typing import TYPE_CHECKING, Any, Protocol

from cudag.annotation.config import AnnotatedElement, AnnotatedTask, AnnotationConfig
from cudag.core.task import BaseTask, TaskContext, TaskSample, TestCase
from cudag.prompts.tools import ToolCall

if TYPE_CHECKING:
    from cudag.core.renderer import BaseRenderer


class IconInfo(Protocol):
    """Protocol for icon placement info from state."""

    icon_id: str
    center: tuple[int, int]
    bounds: tuple[int, int, int, int]


def make_tool_call(
    action: str, coord: tuple[int, int], wait_time: float = 0
) -> ToolCall:
    """Create a ToolCall based on action string from annotation.

    Args:
        action: Action string from annotation (double_click, left_click, etc.)
        coord: (x, y) pixel coordinates
        wait_time: Wait time in seconds for wait actions

    Returns:
        ToolCall instance for the action
    """
    if action == "double_click":
        return ToolCall.double_click(coord)
    elif action == "left_click":
        return ToolCall.left_click(coord)
    elif action == "right_click":
        return ToolCall.right_click(coord)
    elif action == "wait":
        return ToolCall.wait(wait_time)
    else:
        raise ValueError(f"Unknown action '{action}' - must be one of: double_click, left_click, right_click, wait")


class IconListTaskBase(BaseTask):
    """Abstract base class for tasks targeting iconlist elements.

    This base class handles the common pattern for iconlist tasks:
    1. Iterate over tasks in annotation
    2. For each task targeting an iconlist element, generate one sample per icon
    3. Use task.prompt_template, task.action, task.task_type from annotation
    4. Use element.tolerance_x/y from annotation

    Subclasses must implement:
    - get_annotation_config(): Return the AnnotationConfig
    - get_icons_for_element(): Return icon placements and info for an element
    - generate_state(): Generate the screen state

    Example:
        class ClickIconTask(IconListTaskBase):
            def get_annotation_config(self) -> AnnotationConfig:
                return ANNOTATION_CONFIG

            def get_icons_for_element(
                self, element: AnnotatedElement, state: Any
            ) -> tuple[list[IconInfo], dict[str, dict]]:
                if element.label == "desktop":
                    return state.desktop_icons, get_desktop_icons()
                elif element.label == "taskbar":
                    return state.taskbar_icons, get_taskbar_icons()
                return [], {}

            def generate_state(self, rng: Random, **kwargs) -> Any:
                return DesktopState.generate(rng=rng, **kwargs)
    """

    task_type: str = "iconlist"

    @abstractmethod
    def get_annotation_config(self) -> AnnotationConfig | None:
        """Return the annotation config for this generator.

        Returns:
            AnnotationConfig loaded from annotation.json, or None
        """
        ...

    @abstractmethod
    def get_icons_for_element(
        self, element: AnnotatedElement, state: Any
    ) -> tuple[list[Any], dict[str, dict[str, Any]]]:
        """Get icons and their info for an element.

        Args:
            element: The annotated element (iconlist type)
            state: The generated screen state

        Returns:
            Tuple of (icon_placements, icons_info_dict)
            - icon_placements: List of IconPlacement-like objects with icon_id, center, bounds
            - icons_info_dict: Dict mapping icon_id to {label, required, ...}
        """
        ...

    @abstractmethod
    def generate_state(self, rng: Random, **kwargs: Any) -> Any:
        """Generate the screen state.

        Args:
            rng: Random number generator
            **kwargs: Additional arguments for state generation

        Returns:
            State object for rendering
        """
        ...

    def generate_samples(self, ctx: TaskContext) -> list[TaskSample]:
        """Generate samples for ALL iconlist tasks in annotation.

        Iterates over tasks in annotation.json. For each task targeting an
        iconlist element, generates one sample per icon in that list.

        Args:
            ctx: Task context with RNG, index, output directory

        Returns:
            List of TaskSample, one per icon per iconlist task
        """
        config = self.get_annotation_config()
        if config is None:
            return []

        # Generate state - subclass provides kwargs
        state = self.generate_state(ctx.rng)

        # Render once - shared by all samples
        image, metadata = self.renderer.render(state)
        image_path = self.save_image(image, ctx)

        samples: list[TaskSample] = []

        # Iterate over ALL tasks in annotation (except wait and grounding tasks)
        for task in config.tasks:
            if task.action == "wait":
                continue  # Wait tasks handled separately
            if task.action == "grounding":
                continue  # Grounding tasks handled by GroundingTask

            # Get target element
            element = config.get_element(task.target_element_id)
            if element is None:
                continue

            # Only handle iconlist elements
            if element.element_type != "iconlist":
                continue

            # Get icons for this element from state
            icons_in_state, icons_info = self.get_icons_for_element(element, state)
            if not icons_in_state:
                continue

            tolerance = (element.tolerance_x, element.tolerance_y)

            # Generate a sample for each icon
            for icon in icons_in_state:
                icon_info = icons_info.get(icon.icon_id, {})
                label = icon_info.get("label", icon.icon_id)

                prompt = task.prompt_template.replace("[icon_label]", label)
                click_x, click_y = icon.center

                tool_call = make_tool_call(task.action, (click_x, click_y))

                samples.append(
                    TaskSample(
                        id=self.build_id(ctx, f"_{element.label}_{icon.icon_id}"),
                        image_path=image_path,
                        human_prompt=prompt,
                        tool_call=tool_call,
                        pixel_coords=(click_x, click_y),
                        metadata={
                            "task_type": task.task_type,
                            "element_type": element.element_type,
                            "element_label": element.label,
                            "icon_id": icon.icon_id,
                            "icon_label": label,
                            "icon_bounds": icon.bounds,
                            "ground_truth": (
                                state.to_ground_truth()
                                if hasattr(state, "to_ground_truth")
                                else {}
                            ),
                            "tolerance": list(tolerance),
                        },
                        image_size=config.image_size,
                    )
                )

        return samples

    def generate_sample(self, ctx: TaskContext) -> TaskSample:
        """Generate samples - returns first sample."""
        samples = self.generate_samples(ctx)
        if not samples:
            raise ValueError("No samples generated")
        return samples[0]

    def generate_tests(self, ctx: TaskContext) -> list[TestCase]:
        """Generate test cases for required icons in iconlist tasks.

        Only generates tests for icons marked as required=true in annotation.

        Args:
            ctx: Task context

        Returns:
            List of TestCase for required icons
        """
        config = self.get_annotation_config()
        if config is None:
            return []

        state = self.generate_state(ctx.rng)
        image, metadata = self.renderer.render(state)
        image_path = self.save_image(image, ctx)

        tests: list[TestCase] = []

        for task in config.tasks:
            if task.action == "wait":
                continue

            element = config.get_element(task.target_element_id)
            if element is None or element.element_type != "iconlist":
                continue

            icons_in_state, icons_info = self.get_icons_for_element(element, state)
            tolerance = (element.tolerance_x, element.tolerance_y)

            # Test on required icons only
            for icon in icons_in_state:
                icon_info = icons_info.get(icon.icon_id, {})
                if not icon_info.get("required", False):
                    continue

                label = icon_info.get("label", icon.icon_id)
                prompt = task.prompt_template.replace("[icon_label]", label)
                click_x, click_y = icon.center

                tool_call = make_tool_call(task.action, (click_x, click_y))

                tests.append(
                    TestCase(
                        test_id=f"test_{ctx.index:04d}_{element.label}_{icon.icon_id}",
                        screenshot=image_path,
                        prompt=prompt,
                        expected_action=tool_call.to_dict(),
                        tolerance=tolerance,
                        metadata={
                            "task_type": task.task_type,
                            "element_type": element.element_type,
                            "element_label": element.label,
                            "icon_id": icon.icon_id,
                            "icon_label": label,
                            "icon_bounds": icon.bounds,
                            "image_size": image.size,
                        },
                        pixel_coords=(click_x, click_y),
                    )
                )

        return tests

    def generate_test(self, ctx: TaskContext) -> TestCase:
        """Generate test - returns first."""
        tests = self.generate_tests(ctx)
        if not tests:
            raise ValueError("No tests generated")
        return tests[0]
