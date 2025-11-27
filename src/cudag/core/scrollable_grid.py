# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Derivative works may be released by researchers,
# but original files may not be redistributed or used beyond research purposes.

"""Scrollable data grid abstraction for VLM training.

Provides reusable components for rendering scrollable grids with:
- Column definitions and text wrapping
- Row rendering with variable heights
- Scroll position and viewport calculations
- Scrollbar rendering
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from PIL import Image, ImageDraw, ImageFont


@dataclass
class ColumnDef:
    """Definition for a grid column."""

    id: str
    """Column identifier (matches row dict keys)."""

    label: str
    """Display label for header."""

    x: int
    """X position of column start."""

    align: str = "left"
    """Text alignment: 'left' or 'right'."""


@dataclass
class ScrollableGridGeometry:
    """Geometry for a scrollable grid area."""

    x: int
    """X position of grid top-left."""

    y: int
    """Y position of grid top-left."""

    width: int
    """Total width of grid area."""

    height: int
    """Total height of grid area."""

    padding: int = 0
    """Internal padding."""

    header_height: int = 0
    """Height of fixed header row."""

    scrollbar_width: int = 19
    """Width of scrollbar track."""

    @property
    def content_width(self) -> int:
        """Width available for content (excluding scrollbar)."""
        return self.width - self.scrollbar_width - self.padding * 2

    @property
    def content_height(self) -> int:
        """Height available for content (excluding header)."""
        return self.height - self.header_height - self.padding * 2

    @property
    def center(self) -> tuple[int, int]:
        """Center point of the grid (for scroll actions)."""
        cx = self.x + (self.width - self.scrollbar_width) // 2
        cy = self.y + self.height // 2
        return (cx, cy)


@dataclass
class ScrollState:
    """Scroll position state."""

    page: int = 1
    """Current page number (1-based)."""

    has_more: bool = True
    """Whether more content exists below."""


@dataclass
class RowLayout:
    """Layout information for a rendered row."""

    height: int
    """Rendered height of row."""

    wrapped_text: dict[str, list[str]]
    """Wrapped text lines per column."""

    data: dict[str, str]
    """Original row data."""


class ScrollableGrid:
    """A scrollable data grid that renders rows with text wrapping.

    Usage:
        grid = ScrollableGrid(
            geometry=ScrollableGridGeometry(x=0, y=100, width=800, height=300),
            columns=[
                ColumnDef(id="name", label="Name", x=0),
                ColumnDef(id="value", label="Value", x=200, align="right"),
            ],
            font=ImageFont.truetype("arial.ttf", 12),
        )

        # Render rows
        body_image, row_layouts = grid.render_rows(rows)

        # Get visible portion
        visible = grid.get_visible_slice(body_image, scroll_state)

        # Compose onto base image
        grid.compose_onto(base_image, visible, scroll_state, body_image.height)
    """

    def __init__(
        self,
        geometry: ScrollableGridGeometry,
        columns: Sequence[ColumnDef],
        font: ImageFont.FreeTypeFont,
        cell_padding: int = 3,
        line_color: tuple[int, int, int] = (210, 210, 210),
        text_color: tuple[int, int, int] = (0, 0, 0),
        bg_color: tuple[int, int, int] = (255, 255, 255),
    ):
        """Initialize scrollable grid.

        Args:
            geometry: Grid positioning and sizing.
            columns: Column definitions.
            font: Font for rendering text.
            cell_padding: Padding inside each cell.
            line_color: Color for grid lines.
            text_color: Color for text.
            bg_color: Background color.
        """
        self.geometry = geometry
        self.columns = list(columns)
        self.font = font
        self.cell_padding = cell_padding
        self.line_color = line_color
        self.text_color = text_color
        self.bg_color = bg_color

        # Compute column widths
        self._column_widths = self._compute_column_widths()
        self._line_height = self._compute_line_height()

    def _compute_column_widths(self) -> list[int]:
        """Compute widths from column x positions."""
        widths: list[int] = []
        total_width = self.geometry.content_width
        for i, col in enumerate(self.columns):
            if i + 1 < len(self.columns):
                widths.append(self.columns[i + 1].x - col.x)
            else:
                widths.append(total_width - col.x)
        return widths

    def _compute_line_height(self) -> int:
        """Get line height from font metrics."""
        ascent, descent = self.font.getmetrics()
        return int(ascent) + int(descent)

    def _wrap_text(self, text: str, max_width: int) -> list[str]:
        """Wrap text to fit within max_width pixels."""
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if self.font.getlength(candidate) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _compute_row_height(self, row: dict[str, str]) -> tuple[int, dict[str, list[str]]]:
        """Calculate row height and wrapped text for all columns."""
        wrapped: dict[str, list[str]] = {}
        max_lines = 1
        for idx, col in enumerate(self.columns):
            width = self._column_widths[idx]
            lines = self._wrap_text(
                row.get(col.id, ""),
                max_width=max(width - self.cell_padding * 2, 10),
            )
            wrapped[col.id] = lines
            max_lines = max(max_lines, len(lines))
        height = max_lines * self._line_height + self.cell_padding * 2
        return height, wrapped

    def render_rows(self, rows: Sequence[dict[str, str]]) -> tuple[Image.Image, list[RowLayout]]:
        """Render all rows to a body image.

        Args:
            rows: List of row data dicts.

        Returns:
            (body_image, row_layouts) - The rendered image and layout info.
        """
        # First pass: compute layouts
        row_layouts: list[RowLayout] = []
        total_height = 0
        for row in rows:
            height, wrapped = self._compute_row_height(row)
            row_layouts.append(RowLayout(height=height, wrapped_text=wrapped, data=row))
            total_height += height

        # Create body image
        body_width = sum(self._column_widths)
        body_image = Image.new("RGB", (body_width, max(total_height, 1)), color=self.bg_color)
        draw = ImageDraw.Draw(body_image)

        # Second pass: render
        y = 0
        for layout in row_layouts:
            for col_idx, col in enumerate(self.columns):
                x_start = col.x
                x_end = col.x + self._column_widths[col_idx]
                lines = layout.wrapped_text[col.id]
                for line_idx, line in enumerate(lines):
                    if col.align == "right":
                        text_width = int(self.font.getlength(line))
                        text_x = max(x_end - self.cell_padding - text_width, x_start + self.cell_padding)
                    else:
                        text_x = x_start + self.cell_padding
                    text_y = y + self.cell_padding + line_idx * self._line_height
                    draw.text((text_x, text_y), line, font=self.font, fill=self.text_color)

            y += layout.height
            # Horizontal line after row
            draw.line([(0, y - 1), (body_width, y - 1)], fill=self.line_color)

        # Vertical column separators
        for col in self.columns:
            draw.line([(col.x, 0), (col.x, total_height)], fill=self.line_color)

        return body_image, row_layouts

    def get_scroll_offset(
        self,
        scroll_state: ScrollState,
        content_height: int,
    ) -> int:
        """Calculate scroll offset from scroll state.

        Args:
            scroll_state: Current scroll state.
            content_height: Total height of content.

        Returns:
            Pixel offset from top.
        """
        visible_height = self.geometry.content_height
        max_offset = max(content_height - visible_height, 0)

        if not scroll_state.has_more:
            return max_offset

        page_height = max(visible_height, 1)
        offset = max((scroll_state.page - 1) * page_height, 0)
        return min(offset, max_offset)

    def get_visible_slice(
        self,
        body_image: Image.Image,
        scroll_state: ScrollState,
    ) -> Image.Image:
        """Get visible portion of body image.

        Args:
            body_image: Full rendered body.
            scroll_state: Current scroll state.

        Returns:
            Cropped image for visible viewport.
        """
        visible_height = self.geometry.content_height
        start_offset = self.get_scroll_offset(scroll_state, body_image.height)

        if body_image.height <= visible_height:
            canvas = Image.new("RGB", (body_image.width, visible_height), color=self.bg_color)
            canvas.paste(body_image, (0, 0))
            return canvas

        end_offset = min(start_offset + visible_height, body_image.height)
        cropped = body_image.crop((0, start_offset, body_image.width, end_offset))

        if cropped.height == visible_height:
            return cropped

        canvas = Image.new("RGB", (body_image.width, visible_height), color=self.bg_color)
        canvas.paste(cropped, (0, 0))
        return canvas

    def get_visible_row_indices(
        self,
        row_layouts: Sequence[RowLayout],
        scroll_state: ScrollState,
        content_height: int,
    ) -> list[int]:
        """Get indices of rows visible in current viewport.

        Args:
            row_layouts: Layout info for all rows.
            scroll_state: Current scroll state.
            content_height: Total content height.

        Returns:
            List of visible row indices.
        """
        start_offset = self.get_scroll_offset(scroll_state, content_height)
        end_offset = start_offset + self.geometry.content_height
        visible: list[int] = []

        y = 0
        for idx, layout in enumerate(row_layouts):
            row_top = y
            row_bottom = y + layout.height
            if row_bottom > start_offset and row_top < end_offset:
                visible.append(idx)
            y = row_bottom

        return visible

    def render_scrollbar(
        self,
        content_height: int,
        scroll_state: ScrollState,
        min_thumb: int = 30,
    ) -> Image.Image:
        """Render scrollbar track with thumb.

        Args:
            content_height: Total content height.
            scroll_state: Current scroll state.
            min_thumb: Minimum thumb height.

        Returns:
            Scrollbar image.
        """
        track_height = self.geometry.content_height
        visible_height = track_height
        width = self.geometry.scrollbar_width

        # Create track
        track = Image.new("RGB", (width, track_height), color=(240, 240, 240))
        draw = ImageDraw.Draw(track)

        if content_height <= 0 or visible_height <= 0:
            return track

        # Calculate thumb size and position
        ratio = visible_height / content_height
        thumb_height = max(min_thumb, int(track_height * ratio))
        max_offset = max(content_height - visible_height, 1)
        start_offset = self.get_scroll_offset(scroll_state, content_height)
        travel = track_height - thumb_height
        thumb_y = int((start_offset / max_offset) * travel) if travel > 0 else 0

        # Draw thumb (thin dark line)
        thumb_width = 2
        thumb_x0 = (width - thumb_width) // 2
        thumb_x1 = thumb_x0 + thumb_width - 1
        draw.rectangle(
            [(thumb_x0, thumb_y), (thumb_x1, thumb_y + thumb_height)],
            fill=(100, 100, 100),
        )

        return track

    def compose_onto(
        self,
        base_image: Image.Image,
        visible_content: Image.Image,
        scroll_state: ScrollState,
        content_height: int,
        header_image: Image.Image | None = None,
    ) -> dict[str, Any]:
        """Compose grid onto base image.

        Args:
            base_image: Base image to paste onto (modified in place).
            visible_content: Visible portion of content.
            scroll_state: Current scroll state.
            content_height: Total content height.
            header_image: Optional header row image.

        Returns:
            Metadata dict with scroll info.
        """
        geom = self.geometry

        # Create grid canvas
        grid_canvas = Image.new("RGB", (geom.width, geom.height), color=self.bg_color)

        # Add header if provided
        y_offset = geom.padding
        if header_image and geom.header_height > 0:
            grid_canvas.paste(header_image, (geom.padding, y_offset))
            y_offset += geom.header_height

        # Add visible content
        grid_canvas.paste(visible_content, (geom.padding, y_offset))

        # Add scrollbar
        if geom.scrollbar_width > 0:
            scrollbar = self.render_scrollbar(content_height, scroll_state)
            grid_canvas.paste(
                scrollbar,
                (geom.width - geom.scrollbar_width, geom.padding),
            )

        # Paste onto base
        base_image.paste(grid_canvas, (geom.x, geom.y))

        # Return metadata
        start_offset = self.get_scroll_offset(scroll_state, content_height)
        max_offset = max(content_height - geom.content_height, 0)

        return {
            "grid_center": geom.center,
            "scroll_offset": start_offset,
            "visible_height": geom.content_height,
            "content_height": content_height,
            "has_more_above": start_offset > 0,
            "has_more_below": start_offset < max_offset,
        }
