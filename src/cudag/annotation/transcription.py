# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""HTML transcription parsing for grid elements.

This module parses HTML table transcriptions from annotations into structured
data that generators can use to create similar synthetic data.

Example:
    from cudag.annotation import parse_transcription

    html = "<table><tr><td>10/07/2025</td><td>John</td></tr></table>"
    table = parse_transcription(html)

    for row in table.rows:
        print([cell.text for cell in row.cells])
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any


@dataclass
class TranscriptionCell:
    """A single cell from a transcribed table."""

    text: str
    """Full cell text with line breaks converted to spaces."""

    lines: list[str] = field(default_factory=list)
    """Cell content split by <br/> tags, preserving multi-line data."""

    @property
    def first_line(self) -> str:
        """Get first line of cell (useful for primary value)."""
        return self.lines[0] if self.lines else self.text

    @property
    def is_empty(self) -> bool:
        """Check if cell has no content."""
        return not self.text.strip()

    @property
    def is_currency(self) -> bool:
        """Check if cell appears to be a currency value."""
        return bool(re.match(r"^\$?[\d,]+\.?\d*$", self.text.strip()))

    @property
    def is_date(self) -> bool:
        """Check if cell appears to be a date (MM/DD/YYYY or similar)."""
        return bool(re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", self.text.strip()))

    @property
    def is_time(self) -> bool:
        """Check if cell appears to be a time (e.g., 11:16a, 3:25p)."""
        return bool(re.match(r"^\d{1,2}:\d{2}[ap]?m?$", self.text.strip(), re.I))


@dataclass
class TranscriptionRow:
    """A single row from a transcribed table."""

    cells: list[TranscriptionCell] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.cells)

    def __getitem__(self, index: int) -> TranscriptionCell:
        return self.cells[index]

    def get(self, index: int, default: str = "") -> str:
        """Get cell text by index with default."""
        if 0 <= index < len(self.cells):
            return self.cells[index].text
        return default

    @property
    def values(self) -> list[str]:
        """Get all cell values as strings."""
        return [cell.text for cell in self.cells]


@dataclass
class ParsedTranscription:
    """Structured data parsed from an HTML table transcription."""

    rows: list[TranscriptionRow] = field(default_factory=list)
    """All data rows (excludes header if detected)."""

    headers: list[str] = field(default_factory=list)
    """Header row values (if <thead> was present)."""

    raw_html: str = ""
    """Original HTML for reference."""

    @property
    def num_rows(self) -> int:
        """Number of data rows."""
        return len(self.rows)

    @property
    def num_cols(self) -> int:
        """Number of columns (from first row or headers)."""
        if self.headers:
            return len(self.headers)
        if self.rows:
            return len(self.rows[0])
        return 0

    def column(self, index: int) -> list[str]:
        """Get all values from a specific column."""
        return [row.get(index) for row in self.rows]

    def sample_values(self, col_index: int, max_samples: int = 10) -> list[str]:
        """Get sample non-empty values from a column."""
        values = []
        for row in self.rows:
            val = row.get(col_index).strip()
            if val and val not in values:
                values.append(val)
                if len(values) >= max_samples:
                    break
        return values

    def infer_column_types(self) -> list[str]:
        """Infer data types for each column based on content.

        Returns:
            List of type hints: 'date', 'time', 'currency', 'text', 'multiline'
        """
        if not self.rows:
            return []

        types = []
        for col_idx in range(self.num_cols):
            # Check first few non-empty cells
            col_type = "text"
            for row in self.rows[:5]:
                if col_idx >= len(row.cells):
                    continue
                cell = row.cells[col_idx]
                if cell.is_empty:
                    continue

                if len(cell.lines) > 1:
                    col_type = "multiline"
                    break
                elif cell.is_date:
                    col_type = "date"
                    break
                elif cell.is_time:
                    col_type = "time"
                    break
                elif cell.is_currency:
                    col_type = "currency"
                    break

            types.append(col_type)
        return types

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "headers": self.headers,
            "rows": [
                [{"text": c.text, "lines": c.lines} for c in row.cells]
                for row in self.rows
            ],
            "num_rows": self.num_rows,
            "num_cols": self.num_cols,
        }


class _TableHTMLParser(HTMLParser):
    """Internal HTML parser for table extraction."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[TranscriptionRow] = []
        self.headers: list[str] = []
        self._current_row: TranscriptionRow | None = None
        self._current_cell_lines: list[str] = []
        self._current_cell_text: str = ""
        self._in_thead = False
        self._in_tbody = False
        self._in_cell = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "thead":
            self._in_thead = True
        elif tag == "tbody":
            self._in_tbody = True
        elif tag == "tr":
            self._current_row = TranscriptionRow()
        elif tag in ("td", "th"):
            self._in_cell = True
            self._current_cell_lines = []
            self._current_cell_text = ""
        elif tag == "br":
            # Line break within cell - save current text as a line
            if self._in_cell and self._current_cell_text:
                self._current_cell_lines.append(self._current_cell_text.strip())
                self._current_cell_text = ""

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "thead":
            self._in_thead = False
        elif tag == "tbody":
            self._in_tbody = False
        elif tag == "tr":
            if self._current_row is not None:
                # If in thead and no headers yet, use first row as headers
                if self._in_thead and not self.headers:
                    self.headers = [c.text for c in self._current_row.cells]
                else:
                    self.rows.append(self._current_row)
                self._current_row = None
        elif tag in ("td", "th"):
            if self._in_cell and self._current_row is not None:
                # Finalize the current cell
                if self._current_cell_text:
                    self._current_cell_lines.append(self._current_cell_text.strip())

                # Build cell with text and lines
                full_text = " ".join(self._current_cell_lines)
                cell = TranscriptionCell(
                    text=full_text,
                    lines=self._current_cell_lines.copy(),
                )
                self._current_row.cells.append(cell)

            self._in_cell = False
            self._current_cell_lines = []
            self._current_cell_text = ""

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell_text += data


def parse_transcription(html: str) -> ParsedTranscription:
    """Parse HTML table transcription into structured data.

    Args:
        html: HTML string containing a <table> element

    Returns:
        ParsedTranscription with rows, cells, and inferred types

    Example:
        >>> html = "<table><tr><td>10/07/2025</td><td>$54.58</td></tr></table>"
        >>> table = parse_transcription(html)
        >>> table.rows[0].cells[0].text
        '10/07/2025'
        >>> table.rows[0].cells[0].is_date
        True
    """
    if not html or not html.strip():
        return ParsedTranscription(raw_html=html)

    parser = _TableHTMLParser()
    try:
        parser.feed(html)
    except Exception:
        # Return empty on parse error
        return ParsedTranscription(raw_html=html)

    return ParsedTranscription(
        rows=parser.rows,
        headers=parser.headers,
        raw_html=html,
    )


def parse_text_transcription(text: str) -> str:
    """Parse plain text transcription (non-table elements).

    For text elements, the transcription is just unstructured text.
    This function strips whitespace and returns the clean text.

    Args:
        text: Raw transcription text

    Returns:
        Cleaned text string
    """
    if not text:
        return ""
    return text.strip()
