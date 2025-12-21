# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Runtime annotation configuration for data-driven generators.

This module provides AnnotationConfig, which loads annotation.json at runtime
and provides structured access to elements, icons, tasks, tolerances, and
transcriptions.

Example:
    from cudag.annotation import AnnotationConfig

    # Load from assets/annotations folder
    config = AnnotationConfig.load(Path("assets/annotations"))

    # Access icons from an iconlist element
    for icon in config.get_icons("desktop"):
        print(f"{icon.label} at ({icon.center_x}, {icon.center_y})")

    # Get task templates
    for task in config.tasks:
        prompt = task.render_prompt(icon_label="Open Dental")

    # Access grid transcription data
    grid = config.get_element_by_label("patient-account")
    if grid and grid.transcription:
        for row in grid.transcription.rows:
            print([cell.text for cell in row.cells])
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cudag.annotation.transcription import (
    ParsedTranscription,
    parse_text_transcription,
    parse_transcription,
)


@dataclass
class AnnotatedIcon:
    """Single icon within an iconlist element."""

    center_x: int
    """X coordinate of icon center (relative to element bbox or absolute)."""

    center_y: int
    """Y coordinate of icon center (relative to element bbox or absolute)."""

    label: str = ""
    """Icon label for prompts (e.g., 'Open Dental', 'recycle bin')."""

    required: bool = False
    """If True, always include this icon even when varyN is enabled."""

    icon_file_id: str = ""
    """ID to map to icon image file (e.g., 'od' -> icon-tb-od.png)."""

    # Parent element info (set after parsing)
    element_id: str = ""
    element_label: str = ""
    bbox_offset: tuple[int, int] = (0, 0)

    @property
    def absolute_center(self) -> tuple[int, int]:
        """Get absolute center coordinates (bbox offset + relative center)."""
        return (
            self.bbox_offset[0] + self.center_x,
            self.bbox_offset[1] + self.center_y,
        )


@dataclass
class AnnotatedElement:
    """Parsed UI element from annotation with full metadata."""

    id: str
    element_type: str
    bbox: tuple[int, int, int, int]  # x, y, width, height
    label: str = ""

    # Icon list properties
    icons: list[AnnotatedIcon] = field(default_factory=list)
    icon_width: int = 0
    icon_height: int = 0

    # VaryN feature: show random subset of icons
    vary_n: bool = False
    """If True, show a random subset of icons instead of all."""

    random_order: bool = False
    """If True, shuffle the order of icons."""

    layout: str = ""
    """Layout style: 'stacked', 'sparse', 'random', or empty for default."""

    # Grid properties
    rows: int = 0
    """Number of rows for grid elements."""

    cols: int = 0
    """Number of columns for grid elements."""

    col_widths: list[float] = field(default_factory=list)
    """Relative column widths (should sum to 1.0)."""

    row_heights: list[float] = field(default_factory=list)
    """Relative row heights (should sum to 1.0)."""

    selectable_cell: bool = False
    """If True, individual grid cells are selectable."""

    first_row_header: bool = False
    """If True, first row is a fixed header (doesn't scroll)."""

    last_col_scroll: bool = False
    """If True, last column is reserved for vertical scrollbar."""

    last_row_scroll: bool = False
    """If True, last row is reserved for horizontal scrollbar."""

    hide_grid_lines: bool = False
    """If True, don't draw grid lines between cells."""

    show_grid_lines: bool = False
    """If True, draw grid lines between cells."""

    scrollable: bool = False
    """If True, this element supports scrolling."""

    # Tolerance from annotation (in pixels)
    tolerance_x: int = 0
    tolerance_y: int = 0

    # Mask properties
    mask_color: str | None = None

    # Loading element properties
    loading_image: str | None = None
    """Base64-encoded loading overlay image (data:image/png;base64,...)."""

    # Text properties
    h_align: str = "center"
    v_align: str = "center"

    # Grounding flag
    grounding: bool = False
    """If True, this element is included in grounding tasks."""

    grounding_label: str = ""
    """Human-readable label for grounding tasks (e.g., 'Appts', '◀ Y')."""

    # Transcription data (from OCR annotations)
    ocr: bool = False
    """If True, this element has OCR transcription data."""

    transcription_raw: str = ""
    """Raw transcription string (HTML for grids, plain text for text elements)."""

    transcription: ParsedTranscription | None = None
    """Parsed table transcription for grid elements (None for non-grid elements)."""

    transcription_text: str = ""
    """Plain text transcription for text elements (empty for grids)."""

    @property
    def center(self) -> tuple[int, int]:
        """Center point of the element bounding box."""
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)

    @property
    def tolerance(self) -> tuple[int, int]:
        """Tolerance as (x, y) tuple in pixels."""
        return (self.tolerance_x, self.tolerance_y)

    def get_required_icons(self) -> list[AnnotatedIcon]:
        """Get icons marked as required."""
        return [icon for icon in self.icons if icon.required]

    def get_optional_icons(self) -> list[AnnotatedIcon]:
        """Get icons not marked as required."""
        return [icon for icon in self.icons if not icon.required]

    @property
    def data_rows(self) -> int:
        """Number of rows available for data (excluding header/scroll rows)."""
        count = self.rows
        if self.first_row_header:
            count -= 1
        if self.last_row_scroll:
            count -= 1
        return max(0, count)

    @property
    def data_cols(self) -> int:
        """Number of columns available for data (excluding scroll column)."""
        count = self.cols
        if self.last_col_scroll:
            count -= 1
        return max(0, count)

    @property
    def has_transcription(self) -> bool:
        """Check if this element has transcription data."""
        return self.ocr and bool(self.transcription_raw)

    @property
    def is_grid_with_data(self) -> bool:
        """Check if this is a grid element with parsed table data."""
        return self.element_type == "grid" and self.transcription is not None

    def get_transcription_column(self, col_index: int) -> list[str]:
        """Get all values from a specific transcription column.

        Args:
            col_index: Column index (0-based)

        Returns:
            List of cell text values for that column
        """
        if not self.transcription:
            return []
        return self.transcription.column(col_index)

    def get_transcription_sample(
        self, col_index: int, max_samples: int = 10
    ) -> list[str]:
        """Get sample values from a transcription column.

        Useful for seeding random generators with realistic example data.

        Args:
            col_index: Column index (0-based)
            max_samples: Maximum number of samples to return

        Returns:
            List of unique non-empty values from that column
        """
        if not self.transcription:
            return []
        return self.transcription.sample_values(col_index, max_samples)


@dataclass
class AnnotatedTask:
    """Task template from annotation."""

    id: str
    prompt_template: str
    """Prompt with placeholders like [icon_label]."""

    target_element_id: str
    action: str = "left_click"
    wait_time: float = 0.0
    """Wait time in seconds for wait actions."""

    task_type: str = ""
    """Task type identifier (e.g., 'dclick-desktop-icon', 'load-wait')."""

    def render_prompt(self, **kwargs: str) -> str:
        """Render prompt template with substitutions.

        Args:
            **kwargs: Substitutions like icon_label="Open Dental"

        Returns:
            Rendered prompt string
        """
        result = self.prompt_template
        for key, value in kwargs.items():
            result = result.replace(f"[{key}]", value)
        return result


@dataclass
class AnnotationConfig:
    """Runtime configuration loaded from annotation.json.

    Provides structured access to annotated elements, icons, and tasks
    for data-driven generation.
    """

    screen_name: str
    image_size: tuple[int, int]
    elements: list[AnnotatedElement]
    tasks: list[AnnotatedTask]
    image_path: str = ""

    # Paths to annotation assets
    annotations_dir: Path | None = None

    @classmethod
    def load(cls, annotations_dir: Path | str) -> AnnotationConfig:
        """Load annotation config from a directory.

        Supports two formats:
        1. Legacy format: annotation.json contains screen data directly
        2. Manifest format (v2.0): annotation.json is a manifest pointing to
           screen subfolders, each with its own annotation.json

        Args:
            annotations_dir: Path to annotations directory containing annotation.json

        Returns:
            Loaded AnnotationConfig instance for the first/only screen

        Raises:
            FileNotFoundError: If annotation.json or screen subfolder not found
            ValueError: If manifest contains no screens
        """
        annotations_dir = Path(annotations_dir)
        json_path = annotations_dir / "annotation.json"

        if not json_path.exists():
            raise FileNotFoundError(f"annotation.json not found in {annotations_dir}")

        with open(json_path) as f:
            data = json.load(f)

        # Check for manifest format (v2.0)
        if data.get("type") == "manifest":
            # Manifest format - load first screen from subfolder
            screens = data.get("screens", [])

            if not screens:
                raise ValueError("Manifest contains no screens")

            # Load first screen's annotation
            first_screen = screens[0]
            screen_name = first_screen["name"]
            screen_dir = annotations_dir / screen_name
            screen_path = screen_dir / "annotation.json"

            if not screen_path.exists():
                raise FileNotFoundError(f"Screen annotation not found: {screen_path}")

            with open(screen_path) as f:
                screen_data = json.load(f)

            config = cls._parse_dict(screen_data)
            config.annotations_dir = screen_dir
            return config

        # Legacy format - parse directly
        config = cls._parse_dict(data)
        config.annotations_dir = annotations_dir
        return config

    @classmethod
    def _parse_dict(cls, data: dict[str, Any]) -> AnnotationConfig:
        """Parse annotation from dictionary."""
        elements = [cls._parse_element(el) for el in data.get("elements", [])]
        tasks = [cls._parse_task(t) for t in data.get("tasks", [])]

        image_size = data.get("imageSize", [1920, 1080])

        return cls(
            screen_name=data.get("name") or data.get("screenName", "untitled"),
            image_size=(image_size[0], image_size[1]),
            elements=elements,
            tasks=tasks,
            image_path=data.get("imagePath", ""),
        )

    @classmethod
    def _parse_element(cls, el: dict[str, Any]) -> AnnotatedElement:
        """Parse a single element with icons."""
        bbox = el.get("bbox", {})
        bbox_tuple = (
            bbox.get("x", 0),
            bbox.get("y", 0),
            bbox.get("width", 0),
            bbox.get("height", 0),
        )

        # Parse icons if present (for iconlist type)
        icons: list[AnnotatedIcon] = []
        element_label = el.get("text", "")
        element_id = el.get("id", "")

        for icon_data in el.get("icons", []):
            icon = AnnotatedIcon(
                center_x=icon_data.get("centerX", 0),
                center_y=icon_data.get("centerY", 0),
                label=icon_data.get("label", ""),
                required=icon_data.get("required", False),
                icon_file_id=icon_data.get("iconFileId", ""),
                element_id=icon_data.get("elementId", ""),
                element_label=element_label,
                bbox_offset=(bbox_tuple[0], bbox_tuple[1]),
            )
            icons.append(icon)

        # Parse transcription if present
        ocr_enabled = el.get("ocr", False)
        transcription_raw = el.get("transcription", "")
        element_type = el.get("type", "button")

        # Parse transcription based on element type
        parsed_transcription: ParsedTranscription | None = None
        transcription_text = ""

        if transcription_raw:
            if element_type == "grid":
                # Grid elements have HTML table transcriptions
                parsed_transcription = parse_transcription(transcription_raw)
            else:
                # Text and other elements have plain text transcriptions
                transcription_text = parse_text_transcription(transcription_raw)

        return AnnotatedElement(
            id=element_id,
            element_type=el.get("type", "button"),
            bbox=bbox_tuple,
            label=element_label,
            icons=icons,
            icon_width=el.get("iconWidth", 0),
            icon_height=el.get("iconHeight", 0),
            vary_n=el.get("varyN", False),
            random_order=el.get("randomOrder", False),
            layout=el.get("layout", ""),
            rows=el.get("rows", 0),
            cols=el.get("cols", 0),
            col_widths=el.get("colWidths", []),
            row_heights=el.get("rowHeights", []),
            selectable_cell=el.get("selectableCell", False),
            first_row_header=el.get("firstRowHeader", False),
            last_col_scroll=el.get("lastColScroll", False),
            last_row_scroll=el.get("lastRowScroll", False),
            hide_grid_lines=el.get("hideGridLines", False),
            show_grid_lines=el.get("showGridLines", False),
            scrollable=el.get("scrollable", False),
            tolerance_x=el.get("toleranceX", 0),
            tolerance_y=el.get("toleranceY", 0),
            mask_color=el.get("maskColor"),
            loading_image=el.get("loadingImage"),
            h_align=el.get("hAlign", "center"),
            v_align=el.get("vAlign", "center"),
            grounding=el.get("grounding", False),
            grounding_label=el.get("groundingLabel", ""),
            ocr=ocr_enabled,
            transcription_raw=transcription_raw,
            transcription=parsed_transcription,
            transcription_text=transcription_text,
        )

    @classmethod
    def _parse_task(cls, t: dict[str, Any]) -> AnnotatedTask:
        """Parse a single task."""
        return AnnotatedTask(
            id=t.get("id", ""),
            prompt_template=t.get("prompt", ""),
            target_element_id=t.get("targetElementId", ""),
            action=t.get("action", "left_click"),
            wait_time=float(t.get("waitTime", 0)),
            task_type=t.get("taskType", ""),
        )

    def get_element(self, element_id: str) -> AnnotatedElement | None:
        """Get element by ID."""
        for el in self.elements:
            if el.id == element_id:
                return el
        return None

    def get_element_by_label(self, label: str) -> AnnotatedElement | None:
        """Get element by label (text field)."""
        for el in self.elements:
            if el.label == label:
                return el
        return None

    def get_icons(self, element_label: str) -> list[AnnotatedIcon]:
        """Get all icons from an element by its label.

        Args:
            element_label: The 'text' field of the iconlist element (e.g., 'desktop', 'taskbar')

        Returns:
            List of AnnotatedIcon objects
        """
        for el in self.elements:
            if el.label == element_label:
                return el.icons
        return []

    def get_icon_by_label(
        self, element_label: str, icon_label: str
    ) -> AnnotatedIcon | None:
        """Get a specific icon by element label and icon label.

        Args:
            element_label: The element's text (e.g., 'desktop')
            icon_label: The icon's label (e.g., 'open dental')

        Returns:
            AnnotatedIcon or None if not found
        """
        icons = self.get_icons(element_label)
        icon_label_lower = icon_label.lower()
        for icon in icons:
            if icon.label.lower() == icon_label_lower:
                return icon
        return None

    def get_labeled_icons(self, element_label: str) -> list[AnnotatedIcon]:
        """Get only icons that have labels (non-empty label field).

        Args:
            element_label: The element's text (e.g., 'desktop')

        Returns:
            List of AnnotatedIcon objects with non-empty labels
        """
        return [icon for icon in self.get_icons(element_label) if icon.label]

    def get_tasks_for_element(self, element_id: str) -> list[AnnotatedTask]:
        """Get all tasks targeting a specific element."""
        return [t for t in self.tasks if t.target_element_id == element_id]

    def get_loading_element(self) -> AnnotatedElement | None:
        """Get the loading element if one exists."""
        for el in self.elements:
            if el.element_type == "loading":
                return el
        return None

    def get_wait_task(self) -> AnnotatedTask | None:
        """Get the wait task if one exists."""
        for task in self.tasks:
            if task.action == "wait":
                return task
        return None

    def get_click_tasks(self) -> list[AnnotatedTask]:
        """Get all click-type tasks (non-wait actions)."""
        return [t for t in self.tasks if t.action != "wait"]

    def get_task_by_type(self, task_type: str) -> AnnotatedTask | None:
        """Get task by its task_type field."""
        for task in self.tasks:
            if task.task_type == task_type:
                return task
        return None

    def get_tasks_by_type(self, task_type: str) -> list[AnnotatedTask]:
        """Get all tasks with a specific task_type."""
        return [t for t in self.tasks if t.task_type == task_type]

    @property
    def masked_image_path(self) -> Path | None:
        """Path to masked.png if annotations_dir is set."""
        if self.annotations_dir:
            return self.annotations_dir / "masked.png"
        return None

    @property
    def original_image_path(self) -> Path | None:
        """Path to original.png if annotations_dir is set."""
        if self.annotations_dir:
            return self.annotations_dir / "original.png"
        return None

    def to_snake_case(self, name: str) -> str:
        """Convert name to valid Python identifier."""
        clean = re.sub(r"[^a-zA-Z0-9]", "_", name)
        snake = re.sub(r"([a-z])([A-Z])", r"\1_\2", clean).lower()
        snake = re.sub(r"_+", "_", snake)
        if snake and snake[0].isdigit():
            snake = "el_" + snake
        return snake or "unnamed"
