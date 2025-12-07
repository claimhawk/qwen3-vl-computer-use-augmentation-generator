# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Code generation utilities for scaffolding CUDAG projects.

Generates annotation-driven code that loads annotation.json at runtime
via AnnotationConfig, enabling UI updates without regenerating code.
"""

from __future__ import annotations

from cudag.annotation.loader import ParsedAnnotation, ParsedElement, ParsedTask

COPYRIGHT_HEADER = '''# Auto-generated from annotation - feel free to modify.
'''


def generate_screen_py(annotation: ParsedAnnotation) -> str:
    """Generate screen.py with runtime annotation loading."""
    # Identify element types present
    has_grid = any(el.region_type == "grid" for el in annotation.elements)
    has_buttons = any(el.region_type == "button" for el in annotation.elements)
    has_text = any(el.element_type == "text" for el in annotation.elements)

    # Build helper functions based on element types
    helpers: list[str] = []

    if has_grid:
        helpers.append(_generate_grid_helpers())

    if has_buttons:
        helpers.append(_generate_button_helpers())

    if has_text:
        helpers.append(_generate_text_helpers())

    # Always include image path helper
    helpers.append(_generate_image_helpers())

    helpers_str = "\n\n".join(helpers)

    return f'''{COPYRIGHT_HEADER}
"""Screen definition for {annotation.screen_name}.

All UI data comes from the annotator (assets/annotations/annotation.json).
The generator only handles business logic (state randomization, valid click targets).

Data from annotation:
- Element positions, bboxes, tolerances
- Task prompts/templates
- Masked base image

Coordinate scaling:
- Annotation was made on {annotation.image_size} image
- Generator may produce different size images
- All coordinates are scaled at load time
"""

from __future__ import annotations

from pathlib import Path

from cudag.annotation import AnnotatedElement, AnnotatedTask, AnnotationConfig


# -----------------------------------------------------------------------------
# Load Annotation (Single Source of Truth)
# -----------------------------------------------------------------------------

_ANNOTATIONS_DIR = Path(__file__).parent / "assets" / "annotations"

if not _ANNOTATIONS_DIR.exists():
    raise FileNotFoundError(f"Annotations directory not found: {{_ANNOTATIONS_DIR}}")

ANNOTATION_CONFIG = AnnotationConfig.load(_ANNOTATIONS_DIR)


# -----------------------------------------------------------------------------
# Coordinate Scaling
# -----------------------------------------------------------------------------

_ANNOTATION_SIZE = ANNOTATION_CONFIG.image_size  # {annotation.image_size}

# Output size - override these if generating different size images
IMAGE_WIDTH, IMAGE_HEIGHT = _ANNOTATION_SIZE
_GENERATOR_SIZE = (IMAGE_WIDTH, IMAGE_HEIGHT)

_SCALE_X = _GENERATOR_SIZE[0] / _ANNOTATION_SIZE[0]
_SCALE_Y = _GENERATOR_SIZE[1] / _ANNOTATION_SIZE[1]


def scale_coord(x: int | float, y: int | float) -> tuple[int, int]:
    """Scale coordinates from annotation space to generator space."""
    return (int(x * _SCALE_X), int(y * _SCALE_Y))


def scale_bbox(bbox: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Scale bbox (x, y, width, height) from annotation to generator space."""
    x, y, w, h = bbox
    return (int(x * _SCALE_X), int(y * _SCALE_Y), int(w * _SCALE_X), int(h * _SCALE_Y))


def scale_tolerance(tol_x: int, tol_y: int) -> tuple[int, int]:
    """Scale tolerance values from annotation to generator space."""
    return (int(tol_x * _SCALE_X), int(tol_y * _SCALE_Y))


{helpers_str}
'''


def _generate_grid_helpers() -> str:
    """Generate helper functions for grid elements."""
    return '''# -----------------------------------------------------------------------------
# Grid Element Accessors
# -----------------------------------------------------------------------------

def get_grid_element(label: str = "grid") -> AnnotatedElement:
    """Get a grid element by label."""
    el = ANNOTATION_CONFIG.get_element_by_label(label)
    if el is None:
        raise ValueError(f"Grid element '{label}' not found in annotation")
    return el


def get_grid_bbox(label: str = "grid") -> tuple[int, int, int, int]:
    """Get scaled grid bounding box."""
    return scale_bbox(get_grid_element(label).bbox)


def get_grid_dimensions(label: str = "grid") -> tuple[int, int]:
    """Get grid rows and cols from annotation."""
    el = get_grid_element(label)
    return (el.rows, el.cols)


def get_grid_tolerance(label: str = "grid") -> tuple[int, int]:
    """Get scaled grid cell tolerance."""
    el = get_grid_element(label)
    return scale_tolerance(el.tolerance_x, el.tolerance_y)'''


def _generate_button_helpers() -> str:
    """Generate helper functions for button elements."""
    return '''# -----------------------------------------------------------------------------
# Button Element Accessors
# -----------------------------------------------------------------------------

def get_button_element(name: str) -> AnnotatedElement:
    """Get a button element by name."""
    el = ANNOTATION_CONFIG.get_element_by_label(name)
    if el is None:
        raise ValueError(f"Button element '{name}' not found in annotation")
    return el


def get_button_center(name: str) -> tuple[int, int]:
    """Get scaled button center coordinates."""
    el = get_button_element(name)
    return scale_coord(el.center[0], el.center[1])


def get_button_tolerance(name: str) -> tuple[int, int]:
    """Get scaled button tolerance."""
    el = get_button_element(name)
    return scale_tolerance(el.tolerance_x, el.tolerance_y)


def get_all_buttons() -> list[AnnotatedElement]:
    """Get all button elements from annotation."""
    return [el for el in ANNOTATION_CONFIG.elements if el.element_type == "button"]


def get_button_task(button_name: str) -> AnnotatedTask:
    """Get the task for a specific button."""
    el = get_button_element(button_name)
    tasks = ANNOTATION_CONFIG.get_tasks_for_element(el.id)
    if not tasks:
        raise ValueError(f"No task found for button '{button_name}'")
    return tasks[0]


def get_all_button_tasks() -> list[tuple[AnnotatedElement, AnnotatedTask]]:
    """Get all button elements with their tasks."""
    result: list[tuple[AnnotatedElement, AnnotatedTask]] = []
    for el in get_all_buttons():
        tasks = ANNOTATION_CONFIG.get_tasks_for_element(el.id)
        if tasks:
            result.append((el, tasks[0]))
    return result'''


def _generate_text_helpers() -> str:
    """Generate helper functions for text elements."""
    return '''# -----------------------------------------------------------------------------
# Text Element Accessors
# -----------------------------------------------------------------------------

def get_text_element(name: str) -> AnnotatedElement:
    """Get a text element by name."""
    el = ANNOTATION_CONFIG.get_element_by_label(name)
    if el is None:
        raise ValueError(f"Text element '{name}' not found in annotation")
    return el


def get_text_bbox(name: str) -> tuple[int, int, int, int]:
    """Get scaled text element bounding box."""
    el = get_text_element(name)
    return scale_bbox(el.bbox)


def get_text_center(name: str) -> tuple[int, int]:
    """Get scaled text element center position."""
    el = get_text_element(name)
    return scale_coord(el.center[0], el.center[1])'''


def _generate_image_helpers() -> str:
    """Generate helper functions for image paths."""
    return '''# -----------------------------------------------------------------------------
# Image Paths
# -----------------------------------------------------------------------------

def get_masked_image_path() -> Path:
    """Get path to annotator's masked image."""
    path = ANNOTATION_CONFIG.masked_image_path
    if path is None or not path.exists():
        raise FileNotFoundError("masked.png not found in annotations")
    return path


def get_original_image_path() -> Path:
    """Get path to original screenshot."""
    path = ANNOTATION_CONFIG.original_image_path
    if path is None or not path.exists():
        raise FileNotFoundError("original.png not found in annotations")
    return path'''


def generate_state_py(annotation: ParsedAnnotation) -> str:
    """Generate state.py from annotation."""
    class_name = _to_pascal_case(annotation.screen_name) + "State"

    # Extract potential state fields from elements and tasks
    state_fields = _extract_state_fields(annotation)
    fields_str = "\n".join(f"    {f}" for f in state_fields) if state_fields else "    pass"

    return f'''{COPYRIGHT_HEADER}
"""State definition for {annotation.screen_name}."""

from dataclasses import dataclass
from random import Random
from typing import Any

from cudag import BaseState


@dataclass
class {class_name}(BaseState):
    """State for rendering the screen.

    Auto-generated from annotation. Add fields for dynamic content
    that changes between samples (text, selections, etc.).
    """

{fields_str}

    @classmethod
    def generate(cls, rng: Random) -> "{class_name}":
        """Generate a random state for training.

        Override this method to generate realistic variations
        of the screen content.
        """
        return cls()
'''


def _extract_state_fields(annotation: ParsedAnnotation) -> list[str]:
    """Extract potential state fields from annotation."""
    fields: list[str] = []

    # Look for text inputs
    for el in annotation.elements:
        if el.element_type == "textinput":
            field_name = el.python_name + "_text"
            fields.append(f'{field_name}: str = ""')

    # Look for prior states in tasks
    prior_state_fields = set()
    for task in annotation.tasks:
        for prior in task.prior_states:
            field = prior.get("field", "")
            if field:
                prior_state_fields.add(field)

    for field in sorted(prior_state_fields):
        snake = _to_snake_case(field)
        fields.append(f'{snake}: Any = None')

    return fields


def generate_renderer_py(annotation: ParsedAnnotation) -> str:
    """Generate renderer.py using masked.png from annotations."""
    screen_class = _to_pascal_case(annotation.screen_name) + "Screen"
    state_class = _to_pascal_case(annotation.screen_name) + "State"

    return f'''{COPYRIGHT_HEADER}
"""Renderer for {annotation.screen_name}."""

from pathlib import Path
from typing import Any

from PIL import Image

from cudag import BaseRenderer
from screen import get_masked_image_path, IMAGE_WIDTH, IMAGE_HEIGHT
from state import {state_class}


class {screen_class}Renderer(BaseRenderer[{state_class}]):
    """Renderer for {annotation.screen_name} screen.

    Uses masked.png from annotations as base image.
    Customize the render() method to add dynamic content based on state.
    """

    def __init__(self) -> None:
        super().__init__()
        masked_path = get_masked_image_path()
        self._base_image = Image.open(masked_path)
        # Resize if generator uses different size than annotation
        if self._base_image.size != (IMAGE_WIDTH, IMAGE_HEIGHT):
            self._base_image = self._base_image.resize(
                (IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS
            )

    def render(self, state: {state_class}) -> tuple[Image.Image, dict[str, Any]]:
        """Render the screen with the given state.

        Args:
            state: State containing dynamic content

        Returns:
            Tuple of (rendered_image, metadata_dict)
        """
        # Start with base image
        image = self._base_image.copy()

        # TODO: Add dynamic rendering based on state
        # Example:
        # from PIL import ImageDraw
        # draw = ImageDraw.Draw(image)
        # draw.text((x, y), state.some_text, font=font, fill="black", anchor="mm")

        metadata = {{
            "screen_name": "{annotation.screen_name}",
            "image_size": image.size,
        }}

        return image, metadata
'''


def generate_generator_py(annotation: ParsedAnnotation) -> str:
    """Generate generator.py from annotation."""
    screen_class = _to_pascal_case(annotation.screen_name) + "Screen"
    state_class = _to_pascal_case(annotation.screen_name) + "State"
    renderer_class = screen_class + "Renderer"

    task_imports = []
    task_registrations = []
    for task in annotation.tasks:
        task_imports.append(f"from tasks.{task.python_name} import {task.class_name}")
        task_registrations.append(f'    builder.register_task({task.class_name}(config, renderer))')

    task_imports_str = "\n".join(task_imports) if task_imports else "# No tasks defined"
    task_registrations_str = "\n".join(task_registrations) if task_registrations else "    pass"

    return f'''{COPYRIGHT_HEADER}
"""Generator entry point for {annotation.screen_name}."""

import argparse
from pathlib import Path

from cudag import DatasetBuilder, DatasetConfig, run_generator, check_script_invocation

from state import {state_class}
from renderer import {renderer_class}
{task_imports_str}


def main() -> None:
    """Run the generator."""
    check_script_invocation(__file__)

    parser = argparse.ArgumentParser(description="Generate {annotation.screen_name} dataset")
    parser.add_argument("--samples", type=int, default=1000, help="Samples per task")
    parser.add_argument("--output", type=str, default="datasets/{annotation.screen_name}", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    config_path = Path(__file__).parent / "config" / "dataset.yaml"
    config = DatasetConfig.from_yaml(config_path)

    renderer = {renderer_class}()

    builder = DatasetBuilder(
        config=config,
        output_dir=Path(args.output),
        seed=args.seed,
    )

    # Register tasks
{task_registrations_str}

    # Generate dataset
    builder.build(samples_per_task=args.samples)


if __name__ == "__main__":
    main()
'''


def generate_task_py(task: ParsedTask, annotation: ParsedAnnotation) -> str:
    """Generate a task file using screen helpers for coordinates."""
    state_class = _to_pascal_case(annotation.screen_name) + "State"

    # Find target element
    target_el = None
    if task.target_element_id:
        for el in annotation.elements:
            if el.id == task.target_element_id:
                target_el = el
                break

    # Determine which helper to use based on element type
    if target_el:
        if target_el.region_type == "button":
            coord_code = f'pixel_coords = get_button_center("{target_el.label}")'
            tolerance_code = f'tolerance = get_button_tolerance("{target_el.label}")'
            imports = "get_button_center, get_button_tolerance"
        elif target_el.region_type == "grid":
            coord_code = '''# Grid element - coordinates depend on which cell
        grid_bbox = get_grid_bbox()
        # TODO: Calculate cell coordinates based on state
        pixel_coords = (grid_bbox[0] + grid_bbox[2] // 2, grid_bbox[1] + grid_bbox[3] // 2)'''
            tolerance_code = 'tolerance = get_grid_tolerance()'
            imports = "get_grid_bbox, get_grid_tolerance"
        else:
            coord_code = f'''# Get element center
        el = ANNOTATION_CONFIG.get_element_by_label("{target_el.label}")
        pixel_coords = scale_coord(el.center[0], el.center[1])'''
            tolerance_code = f'''el = ANNOTATION_CONFIG.get_element_by_label("{target_el.label}")
        tolerance = scale_tolerance(el.tolerance_x, el.tolerance_y)'''
            imports = "scale_coord, scale_tolerance, ANNOTATION_CONFIG"
    else:
        coord_code = "pixel_coords = (0, 0)  # TODO: specify target coordinates"
        tolerance_code = "tolerance = (50, 50)  # TODO: calculate from element size"
        imports = "scale_coord"

    tool_call = _generate_tool_call(task)

    return f'''{COPYRIGHT_HEADER}
"""Task: {task.prompt or task.python_name}"""

from random import Random
from typing import Any

from cudag import BaseTask, TaskContext, TaskSample, TestCase, ToolCall, normalize_coord

from screen import {imports}, IMAGE_WIDTH, IMAGE_HEIGHT
from state import {state_class}


class {task.class_name}(BaseTask):
    """Task for: {task.prompt}"""

    task_type = "{task.task_type}"

    def generate_sample(self, ctx: TaskContext) -> TaskSample:
        """Generate a training sample."""
        state = {state_class}.generate(ctx.rng)
        image, metadata = self.renderer.render(state)

        # Get target coordinates from annotation
        {coord_code}
        normalized = normalize_coord(pixel_coords, (IMAGE_WIDTH, IMAGE_HEIGHT))

        image_path = self.save_image(image, ctx)

        return TaskSample(
            id=self.build_id(ctx),
            image_path=image_path,
            human_prompt="{task.prompt}",
            tool_call={tool_call},
            pixel_coords=pixel_coords,
            metadata={{
                "task_type": self.task_type,
                **metadata,
            }},
            image_size=image.size,
        )

    def generate_test(self, ctx: TaskContext) -> TestCase:
        """Generate a test case."""
        sample = self.generate_sample(ctx)

        # Get tolerance from annotation
        {tolerance_code}

        return TestCase(
            test_id=f"test_{{sample.id}}",
            screenshot=sample.image_path,
            prompt=sample.human_prompt,
            expected_action=sample.tool_call.to_dict(),
            tolerance=tolerance,
            metadata=sample.metadata,
            pixel_coords=sample.pixel_coords,
        )
'''


def _generate_tool_call(task: ParsedTask) -> str:
    """Generate ToolCall constructor for a task."""
    action = task.action
    params = task.action_params

    if action == "left_click":
        return "ToolCall.left_click(normalized)"
    elif action == "right_click":
        return "ToolCall.right_click(normalized)"
    elif action == "double_click":
        return "ToolCall.double_click(normalized)"
    elif action == "type":
        text = params.get("text", "")
        return f'ToolCall.type("{text}")'
    elif action == "key":
        keys = params.get("keys", [])
        return f"ToolCall.key({keys})"
    elif action == "scroll":
        pixels = params.get("pixels", 100)
        return f"ToolCall.scroll(normalized, pixels={pixels})"
    elif action == "wait":
        ms = params.get("ms", 1000)
        return f"ToolCall.wait(ms={ms})"
    elif action == "drag_to":
        return "ToolCall.drag(normalized, end_coord)"
    elif action == "mouse_move":
        return "ToolCall.mouse_move(normalized)"
    else:
        return f"ToolCall.left_click(normalized)  # TODO: implement {action}"


def generate_tasks_init_py(tasks: list[ParsedTask]) -> str:
    """Generate tasks/__init__.py."""
    imports = []
    exports = []

    for task in tasks:
        imports.append(f"from tasks.{task.python_name} import {task.class_name}")
        exports.append(f'    "{task.class_name}",')

    imports_str = "\n".join(imports) if imports else "# No tasks"
    exports_str = "\n".join(exports) if exports else ""

    return f'''{COPYRIGHT_HEADER}
"""Task definitions for this generator."""

{imports_str}

__all__ = [
{exports_str}
]
'''


def generate_config_yaml(annotation: ParsedAnnotation) -> str:
    """Generate config/dataset.yaml with image output settings."""
    task_counts = "\n".join(
        f"  {task.task_type}: 1000" for task in annotation.tasks
    ) if annotation.tasks else "  # No tasks defined"

    return f'''# Dataset configuration for {annotation.screen_name}
# Auto-generated from annotation

dataset:
  name: {annotation.screen_name}
  version: "1.0.0"
  description: "Training data for {annotation.screen_name}"

# Image output settings
# Defaults to annotation size - override to generate different size images
image:
  width: {annotation.image_size[0]}
  height: {annotation.image_size[1]}

generation:
  seed: 42
  train_split: 0.8
  val_split: 0.1
  test_split: 0.1

tasks:
{task_counts}

# Distribution types (optional)
# distributions:
#   click_button:
#     normal: 0.8
#     edge_case: 0.15
#     adversarial: 0.05
'''


def generate_pyproject_toml(name: str) -> str:
    """Generate pyproject.toml."""
    return f'''[project]
name = "{name}"
version = "0.1.0"
description = "CUDAG generator for {name}"
requires-python = ">=3.12"
dependencies = [
    "cudag",
    "pillow>=10.0.0",
]

[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"
'''


def _to_pascal_case(name: str) -> str:
    """Convert name to PascalCase."""
    parts = name.replace("-", "_").split("_")
    return "".join(p.capitalize() for p in parts if p)


def _to_snake_case(name: str) -> str:
    """Convert name to snake_case."""
    import re
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
