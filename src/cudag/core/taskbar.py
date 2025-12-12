# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Taskbar primitive for Windows-style taskbar rendering.

Provides reusable TaskbarState and TaskbarRenderer for any generator
that needs a taskbar at the bottom of the screen.

The taskbar includes:
- Icons (configurable position, varying N, random order)
- DateTime display (time + date in Windows format)

Example:
    from cudag.core import TaskbarState, TaskbarRenderer

    # Generate random taskbar state
    state = TaskbarState.generate(
        rng=rng,
        icon_config=annotation_config.get_element_by_label("taskbar"),
    )

    # Render onto existing image
    renderer = TaskbarRenderer(assets_dir="assets")
    metadata = renderer.render_onto(image, state)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from random import Random
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from cudag.core.icon import IconPlacement, IconSpec, TASKBAR_ICON


@dataclass
class TaskbarState:
    """State for a Windows-style taskbar.

    Contains icon placements and datetime text for rendering.
    """

    icons: list[IconPlacement] = field(default_factory=list)
    """Icons placed on the taskbar."""

    datetime_text: str = ""
    """DateTime string (e.g., '1:30 PM\\n12/15/2025')."""

    datetime_position: tuple[int, int] = (0, 0)
    """Position for datetime text (x, y)."""

    @classmethod
    def generate(
        cls,
        rng: Random,
        icon_config: Any | None = None,
        datetime_position: tuple[int, int] = (1868, 1043),
        icon_spec: IconSpec | None = None,
        taskbar_left_margin: int = 946,
        taskbar_y_offset: int = 1042,
        icon_gap: int = 8,
        target_date: date | None = None,
    ) -> "TaskbarState":
        """Generate random taskbar state.

        Args:
            rng: Random number generator
            icon_config: AnnotatedElement with icons, varyN, randomOrder settings
            datetime_position: Position for datetime text
            icon_spec: Icon specification (defaults to TASKBAR_ICON)
            taskbar_left_margin: X position where icons start
            taskbar_y_offset: Y position for icons
            icon_gap: Gap between icons
            target_date: Specific date to display (for consistent calendar/taskbar)

        Returns:
            TaskbarState with randomized icons and datetime
        """
        state = cls()
        state.datetime_text = cls._generate_datetime(rng, target_date)
        state.datetime_position = datetime_position

        if icon_config is not None:
            state.icons = cls._place_icons(
                rng,
                icon_config,
                icon_spec or TASKBAR_ICON,
                taskbar_left_margin,
                taskbar_y_offset,
                icon_gap,
            )

        return state

    @classmethod
    def _generate_datetime(cls, rng: Random, target_date: date | None = None) -> str:
        """Generate datetime string in Windows 11 format.

        Args:
            rng: Random number generator for time component
            target_date: Specific date to use (or None for random)

        Returns:
            Formatted datetime string like "1:30 PM\\n12/15/2025"
        """
        # Time is always random
        hour = rng.randint(1, 12)
        minute = rng.randint(0, 59)
        am_pm = rng.choice(["AM", "PM"])

        # Date from target_date or random
        if target_date is not None:
            month = target_date.month
            day = target_date.day
            year = target_date.year
        else:
            month = rng.randint(1, 12)
            day = rng.randint(1, 28)
            year = rng.randint(2024, 2025)

        return f"{hour}:{minute:02d} {am_pm}\n{month}/{day}/{year}"

    @classmethod
    def _place_icons(
        cls,
        rng: Random,
        icon_config: Any,
        icon_spec: IconSpec,
        left_margin: int,
        y_offset: int,
        gap: int,
    ) -> list[IconPlacement]:
        """Place icons based on annotation config settings."""
        placements: list[IconPlacement] = []

        # Get settings from annotation config
        vary_n = getattr(icon_config, "vary_n", False)
        random_order = getattr(icon_config, "random_order", False)
        icons = getattr(icon_config, "icons", [])

        if not icons:
            return placements

        # Build icon list based on varyN setting
        required = [i for i in icons if getattr(i, "required", False)]
        optional = [i for i in icons if not getattr(i, "required", False)]

        if vary_n and optional:
            min_optional = max(1, int(len(optional) * 0.4))
            max_optional = len(optional)
            k = rng.randint(min_optional, max_optional)
            selected_optional = rng.sample(optional, k)
            selected = required + selected_optional
        else:
            selected = required + optional

        # Shuffle if randomOrder is enabled
        if random_order:
            rng.shuffle(selected)

        # Place icons left to right
        x = left_margin
        for icon_data in selected:
            icon_id = getattr(icon_data, "icon_file_id", "") or getattr(
                icon_data, "label", ""
            )
            label = getattr(icon_data, "label", "")

            placements.append(
                IconPlacement(
                    icon_id=icon_id,
                    x=x,
                    y=y_offset,
                    spec=icon_spec,
                    label=label,
                )
            )
            x += icon_spec.width + gap

        return placements

    def get_icon_by_id(self, icon_id: str) -> IconPlacement | None:
        """Find icon by ID."""
        for icon in self.icons:
            if icon.icon_id == icon_id:
                return icon
        return None

    def to_ground_truth(self) -> dict[str, Any]:
        """Export state as ground truth dict."""
        return {
            "icons": [
                {
                    "id": icon.icon_id,
                    "label": icon.label,
                    "bounds": icon.bounds,
                    "center": icon.center,
                }
                for icon in self.icons
            ],
            "datetime": {
                "text": self.datetime_text,
                "position": self.datetime_position,
            },
        }


class TaskbarRenderer:
    """Renderer for Windows-style taskbar.

    Composites taskbar icons and datetime onto existing images.
    Designed to be used as a mixin or called directly.
    """

    def __init__(
        self,
        assets_dir: Path | str = "assets",
        datetime_font_size: int = 9,
    ):
        """Initialize the taskbar renderer.

        Args:
            assets_dir: Path to assets directory containing icons/taskbar/
            datetime_font_size: Font size for datetime text
        """
        self.assets_dir = Path(assets_dir)
        self.datetime_font_size = datetime_font_size
        self._icon_cache: dict[str, Image.Image] = {}
        self._datetime_font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
        self._loaded = False

    def load_assets(self) -> None:
        """Load fonts and icon images."""
        if self._loaded:
            return

        # Load datetime font
        font_path = self.assets_dir / "fonts" / "segoeui.ttf"
        if font_path.exists():
            self._datetime_font = ImageFont.truetype(
                str(font_path), self.datetime_font_size
            )
        else:
            self._datetime_font = ImageFont.load_default()

        # Load taskbar icons
        icons_dir = self.assets_dir / "icons" / "taskbar"
        if icons_dir.exists():
            for icon_path in icons_dir.glob("*.png"):
                icon_id = self._extract_icon_id(icon_path.stem)
                self._icon_cache[icon_id] = Image.open(icon_path).convert("RGBA")

        self._loaded = True

    def _extract_icon_id(self, filename: str) -> str:
        """Extract icon ID from filename.

        Examples:
            icon-tb-od -> od
            icon-od-clean -> od
            taskbar_m365 -> m365
            taskbar_open-dental -> open-dental
        """
        name = filename.lower()
        for prefix in ("icon-", "icon_", "tb-", "tb_", "taskbar_", "taskbar-"):
            if name.startswith(prefix):
                name = name[len(prefix) :]
        for suffix in ("-clean", "_clean"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
        return name

    def render_onto(
        self,
        image: Image.Image,
        state: TaskbarState,
    ) -> dict[str, Any]:
        """Render taskbar onto an existing image.

        Args:
            image: PIL Image to render onto (modified in place)
            state: TaskbarState with icons and datetime

        Returns:
            Metadata dict with icon positions and datetime info
        """
        self.load_assets()

        draw = ImageDraw.Draw(image)

        # Draw icons (paste with alpha compositing)
        for icon in state.icons:
            self._draw_icon(image, icon)

        # Draw datetime
        self._draw_datetime(draw, state)

        return state.to_ground_truth()

    def _draw_icon(self, image: Image.Image, icon: IconPlacement) -> None:
        """Draw a single taskbar icon."""
        icon_id = icon.icon_id.lower()

        # Try to find icon in cache
        icon_img = self._icon_cache.get(icon_id)
        if icon_img is None:
            # Try aliases
            aliases = {
                "open_dental": "od",
                "open-dental": "od",
                "file_explorer": "explorer",
                "microsoft_edge": "edge",
            }
            aliased_id = aliases.get(icon_id)
            if aliased_id:
                icon_img = self._icon_cache.get(aliased_id)

        if icon_img is not None:
            # Ensure icon has alpha channel for compositing
            if icon_img.mode != "RGBA":
                icon_img = icon_img.convert("RGBA")

            # Use alpha channel as mask for proper compositing
            if image.mode == "RGB":
                # For RGB images, paste with alpha mask
                image.paste(icon_img, (icon.x, icon.y), icon_img.split()[3])
            else:
                # For RGBA images, paste directly with alpha
                image.paste(icon_img, (icon.x, icon.y), icon_img)

    def _draw_datetime(self, draw: ImageDraw.ImageDraw, state: TaskbarState) -> None:
        """Draw datetime text."""
        if not state.datetime_text or not self._datetime_font:
            return

        x, y = state.datetime_position
        lines = state.datetime_text.split("\n")

        for i, line in enumerate(lines):
            line_y = y + i * (self.datetime_font_size + 2)
            # Center align text
            bbox = draw.textbbox((0, 0), line, font=self._datetime_font)
            text_width = bbox[2] - bbox[0]
            text_x = x - text_width // 2
            draw.text((text_x, line_y), line, fill="black", font=self._datetime_font)
