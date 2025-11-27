# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Derivative works may be released by researchers,
# but original files may not be redistributed or used beyond research purposes.

"""Base renderer class for image generation.

A Renderer generates images from Screen + State.
Like a View in MVC, it handles the visual presentation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from cudag.core.coords import normalize_coord, pixel_from_normalized

if TYPE_CHECKING:
    from PIL import Image

    from cudag.core.screen import ScreenBase
    from cudag.core.state import BaseState

# Type variable for state
S = TypeVar("S", bound="BaseState")


class BaseRenderer(ABC, Generic[S]):
    """Abstract base class for screen renderers.

    A renderer is responsible for:
    1. Loading base images and assets (fonts, overlays)
    2. Rendering screen state to images
    3. Building metadata for the rendered images

    Example:
        class CalendarRenderer(BaseRenderer[CalendarState]):
            screen_class = CalendarScreen

            def load_assets(self) -> None:
                self.font = ImageFont.truetype(self.asset_path("arial.ttf"), 12)

            def render(self, state: CalendarState) -> tuple[Image, dict]:
                image = self.load_base_image()
                self.draw_calendar_grid(image, state)
                return image, {"month": state.month, "year": state.year}
    """

    screen_class: ClassVar[type[ScreenBase]]
    """The Screen class this renderer is for."""

    def __init__(self, assets_dir: Path | str) -> None:
        """Initialize the renderer.

        Args:
            assets_dir: Path to the assets directory
        """
        self.assets_dir = Path(assets_dir)
        self._base_image: Image.Image | None = None
        self.load_assets()

    @abstractmethod
    def load_assets(self) -> None:
        """Load fonts, base images, and other assets.

        Called during initialization. Override to load your assets.
        Store loaded assets as instance attributes.
        """
        pass

    @abstractmethod
    def render(self, state: S) -> tuple[Image.Image, dict[str, Any]]:
        """Render the screen with given state.

        Args:
            state: Screen state to render

        Returns:
            Tuple of (PIL Image, metadata dict)
        """
        pass

    def asset_path(self, *parts: str) -> Path:
        """Get path to an asset file.

        Args:
            *parts: Path components relative to assets_dir

        Returns:
            Full path to the asset
        """
        return self.assets_dir.joinpath(*parts)

    def load_base_image(self) -> Image.Image:
        """Load and return a copy of the base image.

        Uses the base_image defined in the Screen's Meta class.

        Returns:
            Copy of the base image (safe to modify)
        """
        from PIL import Image

        if self._base_image is None:
            base_path = self.screen_class.meta().base_image
            if isinstance(base_path, str):
                base_path = self.asset_path(base_path)
            self._base_image = Image.open(base_path).convert("RGB")

        return self._base_image.copy()

    def normalize(
        self,
        pixel: tuple[int, int],
        image_size: tuple[int, int] | None = None,
    ) -> tuple[int, int]:
        """Normalize pixel coordinates to RU [0, 1000].

        Args:
            pixel: (x, y) pixel coordinates
            image_size: Image dimensions, or use screen size from Meta

        Returns:
            Normalized (x, y) coordinates
        """
        if image_size is None:
            image_size = self.screen_class.meta().size
        return normalize_coord(pixel, image_size)

    def to_pixel(
        self,
        normalized: tuple[int, int],
        image_size: tuple[int, int] | None = None,
    ) -> tuple[int, int]:
        """Convert normalized RU coordinates to pixels.

        Args:
            normalized: (x, y) coordinates in [0, 1000]
            image_size: Image dimensions, or use screen size from Meta

        Returns:
            Pixel (x, y) coordinates
        """
        if image_size is None:
            image_size = self.screen_class.meta().size
        return pixel_from_normalized(normalized, image_size)

    def get_region_center(self, region_name: str) -> tuple[int, int]:
        """Get the center pixel coordinates of a region.

        Args:
            region_name: Name of the region on the screen

        Returns:
            (x, y) pixel coordinates of region center
        """
        region = self.screen_class.get_region(region_name)
        return region.bounds.center

    def get_action_point(self, region_name: str, target: Any = None) -> tuple[int, int]:
        """Get the pixel coordinates for an action on a region.

        Args:
            region_name: Name of the region
            target: Optional target (cell index, item, etc.)

        Returns:
            (x, y) pixel coordinates for the action
        """
        region = self.screen_class.get_region(region_name)
        return region.get_action_point(target)

    def build_metadata(self, state: S, **extra: Any) -> dict[str, Any]:
        """Build standard metadata dict for a rendered image.

        Args:
            state: The state that was rendered
            **extra: Additional metadata fields

        Returns:
            Metadata dictionary
        """
        meta = self.screen_class.meta()
        return {
            "screen": meta.name,
            "image_size": {"width": meta.size[0], "height": meta.size[1]},
            "state": state.to_dict(),
            **extra,
        }
