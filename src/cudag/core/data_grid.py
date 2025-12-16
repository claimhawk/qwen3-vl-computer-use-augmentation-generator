# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Composable data grid system for annotation-driven rendering.

Provides composition-based grid classes that respect annotation properties:
- Grid: Base class with text wrapping and annotation-driven column widths
- ScrollableGrid: Adds overflow windowing and scroll behavior
- SelectableRowGrid: Adds row/cell selection behavior

These classes are designed to work with annotation.json properties:
- firstRowHeader: Header row from base image (don't render)
- lastColScroll: Last column reserved for vertical scrollbar
- lastRowScroll: Last row reserved for horizontal scrollbar
- scrollable: Whether grid supports scrolling
- selectable: Whether grid supports row selection
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from PIL import Image, ImageDraw, ImageFont


LINE_HEIGHT_DEFAULT = 14


def wrap_text(
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    """Wrap text to fit within max_width, returning list of lines.

    Handles multi-line input (splits on newlines) and word wrapping.
    """
    if not text:
        return []

    lines: list[str] = []
    for paragraph in str(text).split("\n"):
        if not paragraph:
            lines.append("")
            continue

        words = paragraph.split(" ")
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]

            if width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

    return lines if lines else [""]


@dataclass
class ColumnDef:
    """Column definition for data grid."""

    id: str
    """Column identifier (matches row dict keys)."""

    label: str
    """Display label for header."""

    width_pct: float
    """Column width as percentage (0.0-1.0) of grid width."""

    align: str = "left"
    """Text alignment: 'left', 'right', or 'center'."""


@dataclass
class GridGeometry:
    """Geometry from annotation bbox and properties."""

    x: int
    """X position of grid top-left."""

    y: int
    """Y position of grid top-left."""

    width: int
    """Total width of grid area."""

    height: int
    """Total height of grid area."""

    row_heights: list[float] = field(default_factory=list)
    """Row heights as percentages (from annotation)."""

    col_widths: list[float] = field(default_factory=list)
    """Column widths as percentages (from annotation)."""

    first_row_header: bool = False
    """If True, first row is header from base image (don't render content)."""

    last_col_scroll: bool = False
    """If True, last column is reserved for vertical scrollbar."""

    last_row_scroll: bool = False
    """If True, last row is reserved for horizontal scrollbar."""

    @property
    def header_height(self) -> int:
        """Height of header row in pixels."""
        if not self.first_row_header or not self.row_heights:
            return 0
        return int(self.height * self.row_heights[0])

    @property
    def scroll_col_width(self) -> int:
        """Width of scroll column in pixels."""
        if not self.last_col_scroll or not self.col_widths:
            return 0
        return int(self.width * self.col_widths[-1])

    @property
    def scroll_row_height(self) -> int:
        """Height of scroll row in pixels.

        If last_row_scroll is True and there are more than 2 row_heights,
        use the last row_height. Otherwise use a fixed 15px for the scrollbar.
        """
        if not self.last_row_scroll:
            return 0
        # Only use row_heights[-1] if there are 3+ entries (header, content, scroll)
        if len(self.row_heights) > 2:
            return int(self.height * self.row_heights[-1])
        # Otherwise use a fixed scrollbar height
        return 15

    @property
    def content_x(self) -> int:
        """X start of content area."""
        return self.x

    @property
    def content_y(self) -> int:
        """Y start of content area (after header)."""
        return self.y + self.header_height

    @property
    def content_width(self) -> int:
        """Width available for data columns (excluding scroll column)."""
        return self.width - self.scroll_col_width

    @property
    def content_height(self) -> int:
        """Height available for data rows (excluding header and scroll row)."""
        return self.height - self.header_height - self.scroll_row_height

    @property
    def data_col_count(self) -> int:
        """Number of data columns (excluding scroll column)."""
        count = len(self.col_widths)
        if self.last_col_scroll:
            count -= 1
        return max(0, count)

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        """Full grid bounds as (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)

    @property
    def content_bounds(self) -> tuple[int, int, int, int]:
        """Content area bounds as (x, y, width, height)."""
        return (self.content_x, self.content_y, self.content_width, self.content_height)

    @property
    def center(self) -> tuple[int, int]:
        """Center point of the content area."""
        return (
            self.content_x + self.content_width // 2,
            self.content_y + self.content_height // 2,
        )


@dataclass
class RowLayout:
    """Layout information for a rendered row."""

    height: int
    """Calculated height based on wrapped content."""

    wrapped_cells: list[list[str]]
    """Wrapped text lines per column."""

    data: dict[str, Any]
    """Original row data."""

    y_offset: int = 0
    """Y offset from content start."""


class Grid:
    """Base grid class with text wrapping and annotation-driven columns.

    Handles:
    - Row sizing based on content (text wrapping)
    - Column widths from annotation percentages
    - First row header (preserved from base image)

    Usage:
        geometry = GridGeometry(
            x=10, y=100, width=800, height=400,
            col_widths=[0.15, 0.2, 0.3, 0.35],
            row_heights=[0.05, 0.95],
            first_row_header=True,
        )
        columns = [
            ColumnDef(id="date", label="Date", width_pct=0.15),
            ColumnDef(id="name", label="Name", width_pct=0.2),
            ...
        ]
        grid = Grid(geometry, columns, font)
        rows = grid.render_rows(data)
    """

    def __init__(
        self,
        geometry: GridGeometry,
        columns: Sequence[ColumnDef],
        font: ImageFont.FreeTypeFont,
        cell_padding: int = 2,
        line_height: int = LINE_HEIGHT_DEFAULT,
        text_color: tuple[int, int, int] = (0, 0, 0),
    ):
        """Initialize grid.

        Args:
            geometry: Grid positioning and sizing from annotation.
            columns: Column definitions (should match annotation col_widths).
            font: Font for rendering text.
            cell_padding: Padding inside each cell.
            line_height: Height per line of text.
            text_color: Color for text rendering.
        """
        self.geometry = geometry
        self.columns = list(columns)[:geometry.data_col_count]
        self.font = font
        self.cell_padding = cell_padding
        self.line_height = line_height
        self.text_color = text_color

        # Compute column widths in pixels
        self._col_widths_px = self._compute_column_widths()

    def _compute_column_widths(self) -> list[int]:
        """Compute column widths in pixels from percentages."""
        widths: list[int] = []
        for i in range(self.geometry.data_col_count):
            if i < len(self.geometry.col_widths):
                widths.append(int(self.geometry.width * self.geometry.col_widths[i]))
            elif i < len(self.columns):
                widths.append(int(self.geometry.width * self.columns[i].width_pct))
            else:
                widths.append(50)  # fallback
        return widths

    def _compute_row_layout(self, row_data: dict[str, Any]) -> RowLayout:
        """Compute layout for a single row with text wrapping."""
        wrapped_cells: list[list[str]] = []
        max_lines = 1

        for col_idx, col in enumerate(self.columns):
            if col_idx >= len(self._col_widths_px):
                wrapped_cells.append([])
                continue

            value = str(row_data.get(col.id, ""))
            col_width = self._col_widths_px[col_idx] - self.cell_padding * 2
            lines = wrap_text(value, self.font, max(col_width, 10))
            wrapped_cells.append(lines)
            max_lines = max(max_lines, len(lines))

        height = max_lines * self.line_height + self.cell_padding
        return RowLayout(height=height, wrapped_cells=wrapped_cells, data=row_data)

    def compute_layouts(self, rows: Sequence[dict[str, Any]]) -> list[RowLayout]:
        """Compute layouts for all rows.

        Args:
            rows: List of row data dicts.

        Returns:
            List of RowLayout with heights and wrapped text.
        """
        layouts: list[RowLayout] = []
        y_offset = 0

        for row_data in rows:
            layout = self._compute_row_layout(row_data)
            layout.y_offset = y_offset
            layouts.append(layout)
            y_offset += layout.height

        return layouts

    def total_content_height(self, layouts: Sequence[RowLayout]) -> int:
        """Get total height of all rows."""
        if not layouts:
            return 0
        return sum(layout.height for layout in layouts)

    def render_rows(
        self,
        draw: ImageDraw.ImageDraw,
        layouts: Sequence[RowLayout],
        start_y: int | None = None,
        max_y: int | None = None,
    ) -> None:
        """Render rows to an image draw context.

        Args:
            draw: PIL ImageDraw context.
            layouts: Pre-computed row layouts.
            start_y: Y position to start rendering (default: content_y).
            max_y: Maximum Y position (default: bottom of content area).
        """
        if start_y is None:
            start_y = self.geometry.content_y
        if max_y is None:
            max_y = self.geometry.y + self.geometry.height - self.geometry.scroll_row_height

        y = start_y
        for layout in layouts:
            if y >= max_y:
                break

            x = self.geometry.content_x
            for col_idx, col in enumerate(self.columns):
                if col_idx >= len(layout.wrapped_cells):
                    break

                lines = layout.wrapped_cells[col_idx]
                line_y = y

                for line in lines:
                    if line_y >= max_y:
                        break
                    draw.text(
                        (x + self.cell_padding, line_y),
                        line,
                        font=self.font,
                        fill=self.text_color,
                    )
                    line_y += self.line_height

                if col_idx < len(self._col_widths_px):
                    x += self._col_widths_px[col_idx]

            y += layout.height


@dataclass
class ScrollState:
    """Scroll position state."""

    offset: int = 0
    """Pixel offset from top of content."""

    more_above: bool = False
    """Whether more content exists above viewport."""

    more_below: bool = True
    """Whether more content exists below viewport."""


class ScrollableGrid(Grid):
    """Grid with scrolling/overflow support.

    Extends Grid with:
    - Overflow windowing (only render visible rows)
    - Scroll position tracking
    - Vertical scrollbar in last column
    - Horizontal scrollbar in last row (future)

    Usage:
        grid = ScrollableGrid(geometry, columns, font)
        layouts = grid.compute_layouts(all_rows)
        visible = grid.get_visible_layouts(layouts, scroll_state)
        grid.render_rows(draw, visible)
    """

    def __init__(
        self,
        geometry: GridGeometry,
        columns: Sequence[ColumnDef],
        font: ImageFont.FreeTypeFont,
        cell_padding: int = 2,
        line_height: int = LINE_HEIGHT_DEFAULT,
        text_color: tuple[int, int, int] = (0, 0, 0),
        scrollbar_track_color: tuple[int, int, int] = (240, 240, 240),
        scrollbar_thumb_color: tuple[int, int, int] = (180, 180, 180),
    ):
        """Initialize scrollable grid with scrollbar colors."""
        super().__init__(geometry, columns, font, cell_padding, line_height, text_color)
        self.scrollbar_track_color = scrollbar_track_color
        self.scrollbar_thumb_color = scrollbar_thumb_color

    def render_scrollbar(
        self,
        draw: ImageDraw.ImageDraw,
        total_content_height: int,
        scroll_state: ScrollState,
    ) -> None:
        """Render vertical scrollbar in the last column.

        Args:
            draw: PIL ImageDraw context.
            total_content_height: Total height of all content.
            scroll_state: Current scroll position.
        """
        if not self.geometry.last_col_scroll:
            return

        geom = self.geometry
        scroll_col_width = geom.scroll_col_width
        if scroll_col_width <= 0:
            return

        # Scrollbar position (in the last column, content area only)
        track_x = geom.x + geom.width - scroll_col_width
        track_y = geom.content_y
        track_height = geom.content_height
        track_width = scroll_col_width

        # Draw track background
        draw.rectangle(
            [(track_x, track_y), (track_x + track_width, track_y + track_height)],
            fill=self.scrollbar_track_color,
        )

        # Calculate thumb size and position
        viewport_height = geom.content_height
        if total_content_height <= viewport_height or total_content_height <= 0:
            # No scrolling needed - don't show thumb, just track
            return

        # Thumb height proportional to visible ratio
        thumb_height = max(20, int(track_height * (viewport_height / total_content_height)))

        # Thumb position based on scroll offset
        max_offset = total_content_height - viewport_height
        scroll_ratio = scroll_state.offset / max_offset if max_offset > 0 else 0
        thumb_travel = track_height - thumb_height
        thumb_y = track_y + int(scroll_ratio * thumb_travel)

        # Draw thumb (centered in track)
        thumb_width = max(4, scroll_col_width - 4)
        thumb_x = track_x + (scroll_col_width - thumb_width) // 2

        draw.rectangle(
            [(thumb_x, thumb_y), (thumb_x + thumb_width, thumb_y + thumb_height)],
            fill=self.scrollbar_thumb_color,
        )

    def render_horizontal_scrollbar(
        self,
        draw: ImageDraw.ImageDraw,
        total_content_width: int | None = None,
        scroll_offset_x: int = 0,
    ) -> None:
        """Render horizontal scrollbar in the last row.

        Args:
            draw: PIL ImageDraw context.
            total_content_width: Total width of all content (None = no thumb).
            scroll_offset_x: Current horizontal scroll offset.
        """
        if not self.geometry.last_row_scroll:
            return

        geom = self.geometry
        scroll_row_height = geom.scroll_row_height
        if scroll_row_height <= 0:
            return

        # Scrollbar position (in the last row, full width minus scroll column)
        track_x = geom.x
        track_y = geom.y + geom.height - scroll_row_height
        track_width = geom.content_width
        track_height = scroll_row_height

        # Draw track background
        draw.rectangle(
            [(track_x, track_y), (track_x + track_width, track_y + track_height)],
            fill=self.scrollbar_track_color,
        )

        # Calculate thumb if we have content width info
        viewport_width = geom.content_width
        if total_content_width is None or total_content_width <= viewport_width:
            # No horizontal scrolling needed - just show track
            return

        # Thumb width proportional to visible ratio
        thumb_width = max(20, int(track_width * (viewport_width / total_content_width)))

        # Thumb position based on scroll offset
        max_offset = total_content_width - viewport_width
        scroll_ratio = scroll_offset_x / max_offset if max_offset > 0 else 0
        thumb_travel = track_width - thumb_width
        thumb_x = track_x + int(scroll_ratio * thumb_travel)

        # Draw thumb (centered in track)
        thumb_height = max(4, scroll_row_height - 4)
        thumb_y = track_y + (scroll_row_height - thumb_height) // 2

        draw.rectangle(
            [(thumb_x, thumb_y), (thumb_x + thumb_width, thumb_y + thumb_height)],
            fill=self.scrollbar_thumb_color,
        )

    def get_visible_layouts(
        self,
        layouts: Sequence[RowLayout],
        scroll_state: ScrollState,
    ) -> list[RowLayout]:
        """Get layouts visible in current viewport.

        Args:
            layouts: All row layouts.
            scroll_state: Current scroll position.

        Returns:
            List of visible RowLayout objects.
        """
        if not layouts:
            return []

        visible: list[RowLayout] = []
        viewport_top = scroll_state.offset
        viewport_bottom = viewport_top + self.geometry.content_height

        for layout in layouts:
            row_top = layout.y_offset
            row_bottom = row_top + layout.height

            # Row is visible if it overlaps viewport
            if row_bottom > viewport_top and row_top < viewport_bottom:
                visible.append(layout)

        return visible

    def render_visible(
        self,
        draw: ImageDraw.ImageDraw,
        layouts: Sequence[RowLayout],
        scroll_state: ScrollState,
    ) -> None:
        """Render only visible rows with scroll offset applied.

        Args:
            draw: PIL ImageDraw context.
            layouts: All row layouts.
            scroll_state: Current scroll position.
        """
        visible = self.get_visible_layouts(layouts, scroll_state)
        if not visible:
            return

        max_y = self.geometry.y + self.geometry.height - self.geometry.scroll_row_height

        for layout in visible:
            # Calculate actual Y position with scroll offset
            y = self.geometry.content_y + layout.y_offset - scroll_state.offset
            if y >= max_y:
                break

            x = self.geometry.content_x
            for col_idx, col in enumerate(self.columns):
                if col_idx >= len(layout.wrapped_cells):
                    break

                lines = layout.wrapped_cells[col_idx]
                line_y = y

                for line in lines:
                    if line_y >= max_y:
                        break
                    if line_y >= self.geometry.content_y:  # Don't render above header
                        draw.text(
                            (x + self.cell_padding, line_y),
                            line,
                            font=self.font,
                            fill=self.text_color,
                        )
                    line_y += self.line_height

                if col_idx < len(self._col_widths_px):
                    x += self._col_widths_px[col_idx]

        # Render vertical scrollbar
        total_height = self.total_content_height(layouts)
        self.render_scrollbar(draw, total_height, scroll_state)

        # Render horizontal scrollbar (just track, no thumb since we don't track horizontal scroll)
        self.render_horizontal_scrollbar(draw)

    def compute_scroll_state(
        self,
        layouts: Sequence[RowLayout],
        offset: int = 0,
    ) -> ScrollState:
        """Compute scroll state for given offset.

        Args:
            layouts: All row layouts.
            offset: Desired scroll offset.

        Returns:
            ScrollState with adjusted offset and flags.
        """
        total_height = self.total_content_height(layouts)
        viewport_height = self.geometry.content_height
        max_offset = max(0, total_height - viewport_height)

        # Clamp offset
        offset = max(0, min(offset, max_offset))

        return ScrollState(
            offset=offset,
            more_above=offset > 0,
            more_below=offset < max_offset,
        )


@dataclass
class SelectionState:
    """Selection state for rows/cells."""

    selected_row: int | None = None
    """Currently selected row index (None = no selection)."""

    selected_cell: tuple[int, int] | None = None
    """Currently selected cell as (row, col) (None = no selection)."""


class SelectableRowGrid(ScrollableGrid):
    """Grid with row and cell selection support.

    Extends ScrollableGrid with:
    - Row selection highlighting
    - Cell selection highlighting
    - Selection state tracking

    Usage:
        grid = SelectableRowGrid(geometry, columns, font)
        grid.render_visible(draw, layouts, scroll_state, selection_state)
    """

    def __init__(
        self,
        geometry: GridGeometry,
        columns: Sequence[ColumnDef],
        font: ImageFont.FreeTypeFont,
        cell_padding: int = 2,
        line_height: int = LINE_HEIGHT_DEFAULT,
        text_color: tuple[int, int, int] = (0, 0, 0),
        selection_color: tuple[int, int, int] = (200, 220, 255),
    ):
        """Initialize selectable grid.

        Args:
            selection_color: Background color for selected rows.
        """
        super().__init__(
            geometry, columns, font, cell_padding, line_height, text_color
        )
        self.selection_color = selection_color

    def render_with_selection(
        self,
        draw: ImageDraw.ImageDraw,
        layouts: Sequence[RowLayout],
        scroll_state: ScrollState,
        selection: SelectionState | None = None,
    ) -> None:
        """Render visible rows with selection highlighting.

        Args:
            draw: PIL ImageDraw context.
            layouts: All row layouts.
            scroll_state: Current scroll position.
            selection: Current selection state.
        """
        visible = self.get_visible_layouts(layouts, scroll_state)
        if not visible:
            return

        max_y = self.geometry.y + self.geometry.height - self.geometry.scroll_row_height

        for row_idx, layout in enumerate(visible):
            # Calculate actual Y position with scroll offset
            y = self.geometry.content_y + layout.y_offset - scroll_state.offset
            if y >= max_y:
                break

            # Draw selection background if selected
            if selection and selection.selected_row == row_idx:
                draw.rectangle(
                    [
                        (self.geometry.content_x, max(y, self.geometry.content_y)),
                        (self.geometry.content_x + self.geometry.content_width, min(y + layout.height, max_y)),
                    ],
                    fill=self.selection_color,
                )

            # Render row text
            x = self.geometry.content_x
            for col_idx, col in enumerate(self.columns):
                if col_idx >= len(layout.wrapped_cells):
                    break

                lines = layout.wrapped_cells[col_idx]
                line_y = y

                for line in lines:
                    if line_y >= max_y:
                        break
                    if line_y >= self.geometry.content_y:
                        draw.text(
                            (x + self.cell_padding, line_y),
                            line,
                            font=self.font,
                            fill=self.text_color,
                        )
                    line_y += self.line_height

                if col_idx < len(self._col_widths_px):
                    x += self._col_widths_px[col_idx]

    def get_row_bounds(
        self,
        row_idx: int,
        layouts: Sequence[RowLayout],
        scroll_state: ScrollState,
    ) -> tuple[int, int, int, int] | None:
        """Get bounds of a row in screen coordinates.

        Args:
            row_idx: Row index.
            layouts: All row layouts.
            scroll_state: Current scroll position.

        Returns:
            (x, y, width, height) or None if not visible.
        """
        if row_idx < 0 or row_idx >= len(layouts):
            return None

        layout = layouts[row_idx]
        y = self.geometry.content_y + layout.y_offset - scroll_state.offset

        # Check if visible
        max_y = self.geometry.y + self.geometry.height - self.geometry.scroll_row_height
        if y + layout.height <= self.geometry.content_y or y >= max_y:
            return None

        return (
            self.geometry.content_x,
            max(y, self.geometry.content_y),
            self.geometry.content_width,
            layout.height,
        )

    def get_row_center(
        self,
        row_idx: int,
        layouts: Sequence[RowLayout],
        scroll_state: ScrollState,
    ) -> tuple[int, int] | None:
        """Get center point of a row.

        Args:
            row_idx: Row index.
            layouts: All row layouts.
            scroll_state: Current scroll position.

        Returns:
            (x, y) center or None if not visible.
        """
        bounds = self.get_row_bounds(row_idx, layouts, scroll_state)
        if bounds is None:
            return None
        x, y, w, h = bounds
        return (x + w // 2, y + h // 2)
