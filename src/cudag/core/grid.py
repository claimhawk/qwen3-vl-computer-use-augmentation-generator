# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Derivative works may be released by researchers,
# but original files may not be redistributed or used beyond research purposes.

"""Grid abstraction for UI grids.

Provides a reusable Grid class for any grid-based UI component:
- Calendar day grids
- Data grids/tables
- Spreadsheets
- Game boards

The Grid class handles:
- Geometry (cell positions, sizes, gaps)
- Cell coordinate calculations
- Content/data management
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

# Type variable for cell content
T = TypeVar("T")


@dataclass
class GridGeometry:
    """Defines the physical layout of a grid.

    All measurements are in pixels.
    """

    x: int
    """X position of grid top-left corner."""

    y: int
    """Y position of grid top-left corner."""

    rows: int
    """Number of rows."""

    cols: int
    """Number of columns."""

    cell_width: int
    """Width of each cell."""

    cell_height: int
    """Height of each cell."""

    row_gap: int = 0
    """Gap between rows in pixels."""

    col_gap: int = 0
    """Gap between columns in pixels."""

    @property
    def width(self) -> int:
        """Total grid width including gaps."""
        gaps = self.col_gap * (self.cols - 1) if self.cols > 1 else 0
        return self.cols * self.cell_width + gaps

    @property
    def height(self) -> int:
        """Total grid height including gaps."""
        gaps = self.row_gap * (self.rows - 1) if self.rows > 1 else 0
        return self.rows * self.cell_height + gaps

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        """Grid bounds as (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)

    def cell_position(self, row: int, col: int) -> tuple[int, int]:
        """Get top-left position of a cell.

        Args:
            row: Row index (0-based)
            col: Column index (0-based)

        Returns:
            (x, y) position of cell top-left corner
        """
        x = self.x + col * (self.cell_width + self.col_gap)
        y = self.y + row * (self.cell_height + self.row_gap)
        return (x, y)

    def cell_center(self, row: int, col: int) -> tuple[int, int]:
        """Get center position of a cell.

        Args:
            row: Row index (0-based)
            col: Column index (0-based)

        Returns:
            (x, y) center position
        """
        x, y = self.cell_position(row, col)
        return (x + self.cell_width // 2, y + self.cell_height // 2)

    def cell_bounds(self, row: int, col: int) -> tuple[int, int, int, int]:
        """Get bounds of a cell.

        Args:
            row: Row index (0-based)
            col: Column index (0-based)

        Returns:
            (x, y, width, height) bounds
        """
        x, y = self.cell_position(row, col)
        return (x, y, self.cell_width, self.cell_height)

    def index_to_rowcol(self, index: int) -> tuple[int, int]:
        """Convert linear index to (row, col).

        Args:
            index: Linear index (0 to rows*cols-1)

        Returns:
            (row, col) tuple
        """
        return divmod(index, self.cols)

    def rowcol_to_index(self, row: int, col: int) -> int:
        """Convert (row, col) to linear index.

        Args:
            row: Row index
            col: Column index

        Returns:
            Linear index
        """
        return row * self.cols + col

    def point_to_cell(self, x: int, y: int) -> tuple[int, int] | None:
        """Find which cell contains a point.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            (row, col) if point is in grid, None otherwise
        """
        # Check if point is within grid bounds
        if x < self.x or x >= self.x + self.width:
            return None
        if y < self.y or y >= self.y + self.height:
            return None

        # Calculate column
        rel_x = x - self.x
        col_width_with_gap = self.cell_width + self.col_gap
        col = rel_x // col_width_with_gap
        col_offset = rel_x % col_width_with_gap

        # Check if in gap
        if col_offset >= self.cell_width:
            return None
        if col >= self.cols:
            col = self.cols - 1

        # Calculate row
        rel_y = y - self.y
        row_height_with_gap = self.cell_height + self.row_gap
        row = rel_y // row_height_with_gap
        row_offset = rel_y % row_height_with_gap

        # Check if in gap
        if row_offset >= self.cell_height:
            return None
        if row >= self.rows:
            row = self.rows - 1

        return (row, col)


@dataclass
class GridCell(Generic[T]):
    """A cell in a grid with position and content."""

    row: int
    """Row index."""

    col: int
    """Column index."""

    content: T
    """Cell content (type depends on use case)."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Optional metadata for the cell."""

    @property
    def index(self) -> int:
        """Linear index (assuming standard row-major order)."""
        # This is a convenience property; actual cols should be passed from grid
        raise NotImplementedError("Use grid.rowcol_to_index() instead")


@dataclass
class Grid(Generic[T]):
    """A grid of cells with geometry and content.

    Generic type T is the content type for cells.

    Example:
        # Date grid (calendar)
        geometry = GridGeometry(x=2, y=72, rows=6, cols=7, cell_width=24, cell_height=15)
        grid = Grid(geometry)
        for i, d in enumerate(dates):
            row, col = geometry.index_to_rowcol(i)
            grid.set_cell(row, col, d)

        # Get click position for a date
        cell = grid.find_cell(lambda c: c.content == target_date)
        click_pos = geometry.cell_center(cell.row, cell.col)
    """

    geometry: GridGeometry
    """Grid layout/geometry."""

    cells: list[GridCell[T]] = field(default_factory=list)
    """All cells in the grid."""

    def __post_init__(self) -> None:
        """Initialize empty cells if not provided."""
        if not self.cells:
            for row in range(self.geometry.rows):
                for col in range(self.geometry.cols):
                    self.cells.append(GridCell(row=row, col=col, content=None))  # type: ignore

    def get_cell(self, row: int, col: int) -> GridCell[T] | None:
        """Get cell at position."""
        index = self.geometry.rowcol_to_index(row, col)
        if 0 <= index < len(self.cells):
            return self.cells[index]
        return None

    def set_cell(self, row: int, col: int, content: T, **metadata: Any) -> None:
        """Set cell content at position."""
        index = self.geometry.rowcol_to_index(row, col)
        if 0 <= index < len(self.cells):
            self.cells[index].content = content
            self.cells[index].metadata.update(metadata)

    def find_cell(self, predicate: Any) -> GridCell[T] | None:
        """Find first cell matching predicate.

        Args:
            predicate: Function taking GridCell and returning bool

        Returns:
            First matching cell or None
        """
        for cell in self.cells:
            if predicate(cell):
                return cell
        return None

    def find_cells(self, predicate: Any) -> list[GridCell[T]]:
        """Find all cells matching predicate."""
        return [cell for cell in self.cells if predicate(cell)]

    def cell_center(self, row: int, col: int) -> tuple[int, int]:
        """Get center position of cell (convenience method)."""
        return self.geometry.cell_center(row, col)

    def cell_bounds(self, row: int, col: int) -> tuple[int, int, int, int]:
        """Get bounds of cell (convenience method)."""
        return self.geometry.cell_bounds(row, col)

    def iter_cells(self) -> Any:
        """Iterate over all cells."""
        return iter(self.cells)

    @property
    def total_cells(self) -> int:
        """Total number of cells."""
        return self.geometry.rows * self.geometry.cols
