# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Derivative works may be released by researchers,
# but original files may not be redistributed or used beyond research purposes.

"""Rails-like DSL for screen definitions.

Simple, readable screen definitions with DSL functions.

Example:
    class CalendarScreen(Screen):
        name = "calendar"
        base_image = "calendar.png"
        size = (224, 208)

        day_grid = grid((10, 50, 210, 150), rows=6, cols=7)
        back_month = button((7, 192, 20, 12), label="Back Month")
        scroll_area = scrollable((0, 0, 224, 208), step=100)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from pathlib import Path
from typing import Any, ClassVar

# =============================================================================
# Bounds - represents a rectangular area
# =============================================================================


@dataclass
class Bounds:
    """Rectangular bounds for a region on screen."""

    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        """Center point of the bounds."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def right(self) -> int:
        """Right edge x coordinate."""
        return self.x + self.width

    @property
    def bottom(self) -> int:
        """Bottom edge y coordinate."""
        return self.y + self.height

    def contains(self, point: tuple[int, int]) -> bool:
        """Check if a point is within bounds."""
        px, py = point
        return self.x <= px < self.right and self.y <= py < self.bottom

    @classmethod
    def from_tuple(cls, t: tuple[int, int, int, int]) -> Bounds:
        """Create from (x, y, width, height) tuple."""
        return cls(x=t[0], y=t[1], width=t[2], height=t[3])


# =============================================================================
# Region Base Class
# =============================================================================


@dataclass
class Region(ABC):
    """Base class for interactive screen regions."""

    bounds: Bounds
    name: str = ""

    @abstractmethod
    def get_action_point(self, target: Any = None) -> tuple[int, int]:
        """Get the pixel coordinate for performing an action."""
        pass


# =============================================================================
# Region Types
# =============================================================================


@dataclass
class ClickRegion(Region):
    """A simple clickable region."""

    def get_action_point(self, target: Any = None) -> tuple[int, int]:
        return self.bounds.center


@dataclass
class ButtonRegion(ClickRegion):
    """A clickable button."""

    label: str = ""
    description: str = ""
    tolerance: tuple[int, int] = (5, 5)


@dataclass
class GridRegion(Region):
    """A grid of clickable cells."""

    rows: int = 1
    cols: int = 1
    cell_width: int | None = None
    cell_height: int | None = None
    row_gap: int = 0
    col_gap: int = 0

    def __post_init__(self) -> None:
        if self.cell_width is None:
            total_gaps = self.col_gap * (self.cols - 1) if self.cols > 1 else 0
            self.cell_width = (self.bounds.width - total_gaps) // self.cols
        if self.cell_height is None:
            total_gaps = self.row_gap * (self.rows - 1) if self.rows > 1 else 0
            self.cell_height = (self.bounds.height - total_gaps) // self.rows

    def get_action_point(self, target: tuple[int, int] | int | None = None) -> tuple[int, int]:
        if target is None:
            return self.bounds.center

        if isinstance(target, int):
            row, col = divmod(target, self.cols)
        else:
            row, col = target

        assert self.cell_width is not None
        assert self.cell_height is not None

        x = self.bounds.x + col * (self.cell_width + self.col_gap) + self.cell_width // 2
        y = self.bounds.y + row * (self.cell_height + self.row_gap) + self.cell_height // 2
        return (x, y)

    def cell_bounds(self, row: int, col: int) -> Bounds:
        assert self.cell_width is not None
        assert self.cell_height is not None

        x = self.bounds.x + col * (self.cell_width + self.col_gap)
        y = self.bounds.y + row * (self.cell_height + self.row_gap)
        return Bounds(x=x, y=y, width=self.cell_width, height=self.cell_height)


@dataclass
class ScrollRegion(Region):
    """A scrollable region."""

    scroll_step: int = 100
    direction: str = "vertical"

    def get_action_point(self, target: Any = None) -> tuple[int, int]:
        return self.bounds.center

    def get_scroll_pixels(self, direction: str = "down") -> int:
        amount = self.scroll_step
        if direction in ("up", "left"):
            return -amount
        return amount


@dataclass
class DropdownRegion(Region):
    """A dropdown/select field."""

    items: Sequence[str] = dataclass_field(default_factory=list)
    item_height: int = 20

    def get_action_point(self, target: str | int | None = None) -> tuple[int, int]:
        if target is None:
            return self.bounds.center

        if isinstance(target, str):
            try:
                idx = list(self.items).index(target)
            except ValueError:
                return self.bounds.center
        else:
            idx = target

        x = self.bounds.center[0]
        y = self.bounds.bottom + (idx * self.item_height) + self.item_height // 2
        return (x, y)


# =============================================================================
# DSL Functions - the Rails-like interface
# =============================================================================

BoundsTuple = tuple[int, int, int, int]


def region(bounds: BoundsTuple) -> ClickRegion:
    """Define a simple clickable region.

    Example:
        header = region((0, 0, 100, 50))
    """
    return ClickRegion(bounds=Bounds.from_tuple(bounds))


def button(
    bounds: BoundsTuple,
    label: str = "",
    description: str = "",
    tolerance: tuple[int, int] = (5, 5),
) -> ButtonRegion:
    """Define a button.

    Example:
        back_month = button((7, 192, 20, 12), label="Back Month")
    """
    return ButtonRegion(
        bounds=Bounds.from_tuple(bounds),
        label=label,
        description=description,
        tolerance=tolerance,
    )


def grid(
    bounds: BoundsTuple,
    rows: int = 1,
    cols: int = 1,
    cell_width: int | None = None,
    cell_height: int | None = None,
    row_gap: int = 0,
    col_gap: int = 0,
) -> GridRegion:
    """Define a grid region.

    Example:
        day_grid = grid((10, 50, 210, 150), rows=6, cols=7)
        data_grid = grid((0, 100, 800, 400), rows=10, cols=5, row_gap=2)
    """
    return GridRegion(
        bounds=Bounds.from_tuple(bounds),
        rows=rows,
        cols=cols,
        cell_width=cell_width,
        cell_height=cell_height,
        row_gap=row_gap,
        col_gap=col_gap,
    )


def scrollable(
    bounds: BoundsTuple,
    step: int = 100,
    direction: str = "vertical",
) -> ScrollRegion:
    """Define a scrollable region.

    Example:
        content = scrollable((0, 100, 800, 500), step=100)
    """
    return ScrollRegion(
        bounds=Bounds.from_tuple(bounds),
        scroll_step=step,
        direction=direction,
    )


def dropdown(
    bounds: BoundsTuple,
    items: Sequence[str] | None = None,
    item_height: int = 20,
) -> DropdownRegion:
    """Define a dropdown region.

    Example:
        month_select = dropdown((100, 10, 80, 25), items=["Jan", "Feb", "Mar"])
    """
    return DropdownRegion(
        bounds=Bounds.from_tuple(bounds),
        items=items or [],
        item_height=item_height,
    )


# =============================================================================
# Screen Meta - configuration for screens
# =============================================================================


class ScreenMeta:
    """Metadata for a Screen class."""

    name: str = ""
    base_image: str | Path = ""
    size: tuple[int, int] = (1000, 1000)
    task_types: list[str]

    def __init__(self) -> None:
        self.task_types = []


# =============================================================================
# Screen Base Class
# =============================================================================


class ScreenBase(ABC):
    """Base class for Screen definitions.

    A Screen has many Tasks - this is the core 1:N relationship.
    Each Screen defines the UI layout and can declare which task types it supports.

    Example:
        class CalendarScreen(Screen):
            name = "calendar"
            base_image = "calendar.png"
            size = (224, 208)

            # Regions
            day_grid = grid((10, 50, 210, 150), rows=6, cols=7)
            back_month = button((7, 192, 20, 12), label="Back")

            # Tasks that belong to this screen
            task_types = ["click-day", "click-month", "scroll-calendar"]
    """

    # Class-level attributes that can be set directly
    name: ClassVar[str] = ""
    base_image: ClassVar[str | Path] = ""
    size: ClassVar[tuple[int, int]] = (1000, 1000)
    task_types: ClassVar[list[str]] = []

    # Collected metadata
    _regions: ClassVar[dict[str, Region]] = {}
    _meta: ClassVar[ScreenMeta]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        # Collect regions from class attributes
        regions: dict[str, Region] = {}
        for attr_name, value in cls.__dict__.items():
            if isinstance(value, Region):
                value.name = attr_name
                regions[attr_name] = value

        cls._regions = regions

        # Build meta from class attributes or inner Meta class
        cls._meta = ScreenMeta()

        # Check for inner Meta class (Rails style)
        inner_meta = getattr(cls, "Meta", None)
        if inner_meta:
            for attr in ("name", "base_image", "size", "task_types"):
                if hasattr(inner_meta, attr):
                    setattr(cls._meta, attr, getattr(inner_meta, attr))

        # Also check class-level attributes (simpler style)
        for attr in ("name", "base_image", "size", "task_types"):
            val = cls.__dict__.get(attr)
            if val is not None and val != "" and val != []:
                setattr(cls._meta, attr, val)

        # Default name from class name
        if not cls._meta.name:
            cls._meta.name = cls.__name__.lower().replace("screen", "")

    @classmethod
    def get_region(cls, name: str) -> Region:
        """Get a region by name."""
        if name not in cls._regions:
            raise KeyError(f"Region '{name}' not found in {cls.__name__}")
        return cls._regions[name]

    @classmethod
    def regions(cls) -> dict[str, Region]:
        """Get all regions."""
        return cls._regions.copy()

    @classmethod
    def meta(cls) -> ScreenMeta:
        """Get screen metadata."""
        return cls._meta

    @classmethod
    def get_task_types(cls) -> list[str]:
        """Get task types that belong to this screen."""
        return cls._meta.task_types.copy()

    @abstractmethod
    def render(self, state: Any) -> tuple[Any, dict[str, Any]]:
        """Render the screen with given state."""
        pass


# Alias for cleaner imports
Screen = ScreenBase
