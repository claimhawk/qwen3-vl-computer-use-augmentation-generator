# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Derivative works may be released by researchers,
# but original files may not be redistributed or used beyond research purposes.

"""Base state class for screen state data.

State represents the dynamic data that populates a screen at render time.
Each generator project defines its own State class with relevant fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar


@dataclass
class BaseState:
    """Base class for screen state.

    Subclass this to define the dynamic data for your screen.

    Example:
        @dataclass
        class CalendarState(BaseState):
            year: int
            month: int
            selected_day: int
            current_day: int
            target_day: int

            @property
            def month_name(self) -> str:
                import calendar
                return calendar.month_name[self.month]
    """

    # Subclasses can define validation rules
    _validators: ClassVar[list[str]] = []

    def validate(self) -> list[str]:
        """Validate the state and return list of errors.

        Override in subclass to add custom validation.

        Returns:
            List of error messages (empty if valid)
        """
        return []

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary.

        Useful for serialization and metadata.
        """
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseState:
        """Create state from dictionary."""
        return cls(**data)


@dataclass
class ScrollState(BaseState):
    """Common scroll state for scrollable regions.

    Reusable across different generators that have scrolling.
    """

    scroll_position: int = 0
    """Current scroll offset in pixels."""

    has_more_above: bool = False
    """Whether there's content above the visible area."""

    has_more_below: bool = True
    """Whether there's content below the visible area."""

    page_size: int = 100
    """Visible area height in pixels."""

    content_height: int = 0
    """Total content height in pixels."""

    @property
    def max_scroll(self) -> int:
        """Maximum scroll position."""
        return max(0, self.content_height - self.page_size)

    @property
    def at_top(self) -> bool:
        """Whether scrolled to top."""
        return self.scroll_position <= 0

    @property
    def at_bottom(self) -> bool:
        """Whether scrolled to bottom."""
        return self.scroll_position >= self.max_scroll

    def scroll_by(self, pixels: int) -> ScrollState:
        """Return new state scrolled by given pixels."""
        new_pos = max(0, min(self.scroll_position + pixels, self.max_scroll))
        return ScrollState(
            scroll_position=new_pos,
            has_more_above=new_pos > 0,
            has_more_below=new_pos < self.max_scroll,
            page_size=self.page_size,
            content_height=self.content_height,
        )
