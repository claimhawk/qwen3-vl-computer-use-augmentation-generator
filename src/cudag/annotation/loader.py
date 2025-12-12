# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Annotation loader for parsing Annotator exports."""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO


@dataclass
class ParsedElement:
    """Parsed UI element from annotation."""

    id: str
    element_type: str
    bounds: tuple[int, int, int, int]  # x, y, width, height
    label: str | None = None

    # Grid properties
    rows: int | None = None
    cols: int | None = None
    row_heights: list[float] | None = None
    col_widths: list[float] | None = None

    # Mask properties
    mask: bool = True
    mask_color: str | None = None

    # Export properties
    export_icon: bool = False

    # Text properties
    text: str | None = None
    text_align: str | None = None

    # Computed names for code generation
    python_name: str = ""
    region_type: str = ""

    def __post_init__(self) -> None:
        """Compute derived fields."""
        if not self.python_name:
            self.python_name = self._to_snake_case(self.label or self.id)
        if not self.region_type:
            self.region_type = self._map_region_type()

    def _to_snake_case(self, name: str) -> str:
        """Convert name to valid Python identifier."""
        # Remove non-alphanumeric characters
        clean = re.sub(r"[^a-zA-Z0-9]", "_", name)
        # Convert camelCase to snake_case
        snake = re.sub(r"([a-z])([A-Z])", r"\1_\2", clean).lower()
        # Remove consecutive underscores
        snake = re.sub(r"_+", "_", snake)
        # Ensure it starts with a letter
        if snake and snake[0].isdigit():
            snake = "el_" + snake
        return snake or "unnamed"

    def _map_region_type(self) -> str:
        """Map element type to CUDAG region type."""
        type_mapping = {
            "button": "button",
            "link": "button",
            "tab": "button",
            "menuitem": "button",
            "checkbox": "button",
            "radio": "button",
            "textinput": "region",
            "dropdown": "dropdown",
            "listbox": "dropdown",
            "grid": "grid",
            "icon": "grid",
            "scrollbar": "scrollable",
            "panel": "region",
            "dialog": "region",
            "toolbar": "region",
            "menubar": "region",
            "text": "region",
            "mask": "region",
            "image": "region",
        }
        return type_mapping.get(self.element_type, "region")


@dataclass
class ParsedTask:
    """Parsed task from annotation."""

    id: str
    prompt: str
    target_element_id: str | None = None
    action: str = "left_click"
    action_params: dict[str, Any] = field(default_factory=dict)
    prior_states: list[dict[str, Any]] = field(default_factory=list)

    # Computed names for code generation
    class_name: str = ""
    python_name: str = ""
    task_type: str = ""

    def __post_init__(self) -> None:
        """Compute derived fields."""
        if not self.python_name:
            self.python_name = self._derive_python_name()
        if not self.class_name:
            self.class_name = self._derive_class_name()
        if not self.task_type:
            self.task_type = self._derive_task_type()

    def _derive_python_name(self) -> str:
        """Derive Python identifier from task."""
        # Try to create name from action and target
        base = f"{self.action}_{self.target_element_id or 'element'}"
        # Clean up
        clean = re.sub(r"[^a-zA-Z0-9]", "_", base).lower()
        clean = re.sub(r"_+", "_", clean)
        return clean or "task"

    def _derive_class_name(self) -> str:
        """Derive class name from task."""
        # Convert python_name to PascalCase
        parts = self.python_name.split("_")
        pascal = "".join(p.capitalize() for p in parts if p)
        return f"{pascal}Task"

    def _derive_task_type(self) -> str:
        """Derive task type identifier."""
        return self.python_name.replace("_", "-")


@dataclass
class ParsedAnnotation:
    """Fully parsed annotation data."""

    screen_name: str
    image_size: tuple[int, int]
    elements: list[ParsedElement]
    tasks: list[ParsedTask]
    image_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert back to annotation.json format."""
        return {
            "screenName": self.screen_name,
            "imageSize": list(self.image_size),
            "imagePath": self.image_path,
            "elements": [self._element_to_dict(el) for el in self.elements],
            "tasks": [self._task_to_dict(t) for t in self.tasks],
        }

    def _element_to_dict(self, el: ParsedElement) -> dict[str, Any]:
        """Convert element back to dict format."""
        result: dict[str, Any] = {
            "id": el.id,
            "type": el.element_type,
            "bbox": {
                "x": el.bounds[0],
                "y": el.bounds[1],
                "width": el.bounds[2],
                "height": el.bounds[3],
            },
        }
        if el.label:
            result["text"] = el.label
        if el.rows:
            result["rows"] = el.rows
        if el.cols:
            result["cols"] = el.cols
        if el.row_heights:
            result["rowHeights"] = el.row_heights
        if el.col_widths:
            result["colWidths"] = el.col_widths
        if el.mask_color:
            result["maskColor"] = el.mask_color
        if el.text_align:
            result["textAlign"] = el.text_align
        return result

    def _task_to_dict(self, t: ParsedTask) -> dict[str, Any]:
        """Convert task back to dict format."""
        result: dict[str, Any] = {
            "id": t.id,
            "prompt": t.prompt,
            "action": t.action,
        }
        if t.target_element_id:
            result["targetElementId"] = t.target_element_id
        if t.task_type:
            result["taskType"] = t.task_type
        if t.prior_states:
            result["priorStates"] = t.prior_states
        # Add action params
        if t.action == "type" and "text" in t.action_params:
            result["text"] = t.action_params["text"]
        elif t.action == "key" and "keys" in t.action_params:
            result["keys"] = t.action_params["keys"]
        elif t.action == "scroll" and "pixels" in t.action_params:
            result["scrollPixels"] = t.action_params["pixels"]
        elif t.action == "wait" and "ms" in t.action_params:
            result["waitMs"] = t.action_params["ms"]
        return result


class AnnotationLoader:
    """Load and parse annotation data from various sources."""

    def load(self, path: Path | str | BinaryIO) -> ParsedAnnotation:
        """Load annotation from a file, folder, or stream.

        Args:
            path: Path to annotation.json, annotation.zip, annotation folder,
                  or a file-like object

        Returns:
            Parsed annotation data
        """
        if isinstance(path, (str, Path)):
            path = Path(path)
            if path.is_dir():
                return self._load_folder(path)
            elif path.suffix == ".zip":
                return self._load_zip(path)
            else:
                with open(path) as f:
                    data = json.load(f)
                return self.parse_dict(data)
        else:
            # File-like object - assume ZIP
            return self._load_zip_stream(path)

    def _load_folder(self, path: Path) -> ParsedAnnotation:
        """Load annotation from unpacked folder."""
        annotation_file = path / "annotation.json"
        if not annotation_file.exists():
            raise FileNotFoundError(f"No annotation.json found in {path}")
        with open(annotation_file) as f:
            data = json.load(f)
        return self.parse_dict(data)

    def _load_zip(self, path: Path) -> ParsedAnnotation:
        """Load annotation from ZIP file."""
        with zipfile.ZipFile(path) as zf:
            return self._parse_zip(zf)

    def _load_zip_stream(self, stream: BinaryIO) -> ParsedAnnotation:
        """Load annotation from ZIP stream."""
        with zipfile.ZipFile(stream) as zf:
            return self._parse_zip(zf)

    def _parse_zip(self, zf: zipfile.ZipFile) -> ParsedAnnotation:
        """Parse annotation from opened ZIP file."""
        annotation_file = zf.read("annotation.json")
        data = json.loads(annotation_file.decode("utf-8"))
        return self.parse_dict(data)

    def parse_dict(self, data: dict[str, Any]) -> ParsedAnnotation:
        """Parse annotation from dictionary.

        Args:
            data: Raw annotation dictionary

        Returns:
            Parsed annotation data
        """
        elements = [self._parse_element(el) for el in data.get("elements", [])]
        tasks = [self._parse_task(t, elements) for t in data.get("tasks", [])]

        return ParsedAnnotation(
            screen_name=self._sanitize_name(data.get("screenName", "untitled")),
            image_size=tuple(data.get("imageSize", [1000, 1000])),
            elements=elements,
            tasks=tasks,
            image_path=data.get("imagePath", ""),
        )

    def _parse_element(self, el: dict[str, Any]) -> ParsedElement:
        """Parse a single element."""
        bbox = el.get("bbox", {})
        return ParsedElement(
            id=el.get("id", ""),
            element_type=el.get("type", "button"),
            bounds=(
                bbox.get("x", 0),
                bbox.get("y", 0),
                bbox.get("width", 0),
                bbox.get("height", 0),
            ),
            label=el.get("text"),
            rows=el.get("rows"),
            cols=el.get("cols"),
            row_heights=el.get("rowHeights"),
            col_widths=el.get("colWidths"),
            mask=el.get("mask", True),
            mask_color=el.get("maskColor"),
            export_icon=el.get("exportIcon", False),
            text=el.get("text"),
            text_align=el.get("textAlign"),
        )

    def _parse_task(
        self, t: dict[str, Any], elements: list[ParsedElement]
    ) -> ParsedTask:
        """Parse a single task."""
        action = t.get("action", "left_click")
        action_params: dict[str, Any] = {}

        # Extract action-specific parameters
        if action == "type":
            action_params["text"] = t.get("text", "")
        elif action == "key":
            action_params["keys"] = t.get("keys", [])
        elif action == "scroll":
            action_params["pixels"] = t.get("scrollPixels", 100)
        elif action == "wait":
            action_params["ms"] = t.get("waitMs", 1000)
        elif action in ("drag_to", "move_to"):
            action_params["end_x"] = t.get("endX", 0)
            action_params["end_y"] = t.get("endY", 0)

        return ParsedTask(
            id=t.get("id", ""),
            prompt=t.get("prompt", ""),
            target_element_id=t.get("targetElementId"),
            action=action,
            action_params=action_params,
            prior_states=t.get("priorStates", []),
        )

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use as a Python identifier."""
        clean = re.sub(r"[^a-zA-Z0-9]", "_", name).lower()
        clean = re.sub(r"_+", "_", clean).strip("_")
        return clean or "untitled"
