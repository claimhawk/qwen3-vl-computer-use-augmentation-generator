# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Coordinate system utilities for RU (Resolution Units) normalization.

All coordinates in CUDAG use RU normalized with independent axis scaling.
Both X and Y axes map independently to [0, 1000], matching Qwen3-VL's
coordinate system.

For a 1920x1080 image:
- X range: [0, 1000] (pixel_x / 1920 * 1000)
- Y range: [0, 1000] (pixel_y / 1080 * 1000)

Conversion formulas (independent scaling per axis):
    normalized_x = pixel_x / width * 1000
    normalized_y = pixel_y / height * 1000

To convert back to pixels:
    pixel_x = normalized_x / 1000 * width
    pixel_y = normalized_y / 1000 * height
"""

from __future__ import annotations

import math

# Resolution Units max value for the larger dimension
RU_MAX = 1000


def normalize_coord(
    pixel: tuple[int, int],
    image_size: tuple[int, int],
) -> tuple[int, int]:
    """Convert pixel coordinates to RU (Resolution Units) with independent scaling.

    Both X and Y axes map independently to [0, 1000], matching Qwen3-VL's
    coordinate system where coordinates are normalized to a 1000x1000 grid
    regardless of the original image dimensions.

    Args:
        pixel: (x, y) pixel coordinates
        image_size: (width, height) of the image

    Returns:
        (x, y) normalized coordinates in [0, 1000] range for both axes

    Example:
        For 1920x1080 image, point (960, 540):
        - x_norm = 960 / 1920 * 1000 = 500
        - y_norm = 540 / 1080 * 1000 = 500
    """
    width, height = image_size
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid image size: {image_size}")

    # Independent scaling per axis (Qwen3-VL format)
    x_norm = int(round(pixel[0] / width * RU_MAX))
    y_norm = int(round(pixel[1] / height * RU_MAX))
    return (x_norm, y_norm)


def pixel_from_normalized(
    normalized: tuple[int, int],
    image_size: tuple[int, int],
) -> tuple[int, int]:
    """Convert RU (Resolution Units) coordinates back to pixels.

    Reverses the independent axis scaling used in normalize_coord().

    Args:
        normalized: (x, y) coordinates in RU [0, 1000]
        image_size: (width, height) of the image

    Returns:
        (x, y) pixel coordinates

    Example:
        For 1920x1080 image, RU point (500, 500):
        - x_pixel = 500 / 1000 * 1920 = 960
        - y_pixel = 500 / 1000 * 1080 = 540
    """
    width, height = image_size
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid image size: {image_size}")

    # Reverse independent scaling per axis
    x_pixel = int(round(normalized[0] / RU_MAX * width))
    y_pixel = int(round(normalized[1] / RU_MAX * height))
    return (x_pixel, y_pixel)


def get_normalized_bounds(image_size: tuple[int, int]) -> tuple[int, int]:
    """Get the maximum normalized coordinates for an image.

    With independent axis scaling, both axes always map to [0, 1000].

    Args:
        image_size: (width, height) of the image

    Returns:
        (max_x, max_y) in RU coordinates - always (1000, 1000)

    Example:
        For 1920x1080: returns (1000, 1000)
        For 1080x1920: returns (1000, 1000)
    """
    width, height = image_size
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid image size: {image_size}")

    # Both axes always map to 1000 with independent scaling
    return (RU_MAX, RU_MAX)


def clamp_coord(coord: tuple[int, int], max_val: int = RU_MAX) -> tuple[int, int]:
    """Clamp coordinates to valid range [0, max_val].

    Args:
        coord: (x, y) coordinates
        max_val: Maximum value (default: 1000)

    Returns:
        Clamped (x, y) coordinates
    """
    x = max(0, min(coord[0], max_val))
    y = max(0, min(coord[1], max_val))
    return (x, y)


def coord_distance(a: tuple[int, int], b: tuple[int, int]) -> float:
    """Calculate Euclidean distance between two coordinates.

    Args:
        a: First (x, y) coordinate
        b: Second (x, y) coordinate

    Returns:
        Euclidean distance
    """
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def coord_within_tolerance(
    actual: tuple[int, int],
    expected: tuple[int, int],
    tolerance: int,
) -> bool:
    """Check if actual coordinate is within tolerance of expected.

    Args:
        actual: Actual (x, y) coordinate
        expected: Expected (x, y) coordinate
        tolerance: Maximum allowed distance

    Returns:
        True if within tolerance
    """
    return coord_distance(actual, expected) <= tolerance


def tolerance_to_ru(
    tolerance_pixels: tuple[int, int],
    image_size: tuple[int, int],
) -> tuple[int, int]:
    """Convert pixel tolerance to normalized RU units.

    Uses independent axis scaling to match normalize_coord().

    Args:
        tolerance_pixels: (width, height) tolerance in pixels
        image_size: (width, height) of the image

    Returns:
        Tolerance in RU units [0, 1000]

    Example:
        >>> tolerance_to_ru((50, 30), (1920, 1080))
        (26, 28)
    """
    width, height = image_size
    return (
        int(round(tolerance_pixels[0] / width * RU_MAX)),
        int(round(tolerance_pixels[1] / height * RU_MAX)),
    )


def bounds_to_tolerance(
    bounds: tuple[int, int, int, int],
    scale: float = 0.5,
) -> tuple[int, int]:
    """Calculate tolerance from bounding box dimensions.

    Args:
        bounds: (x, y, width, height) bounding box
        scale: Fraction of dimensions to use (default 0.5 = half size)

    Returns:
        (tolerance_x, tolerance_y) in pixels

    Example:
        >>> bounds_to_tolerance((0, 0, 100, 50), scale=0.5)
        (50, 25)
    """
    _, _, width, height = bounds
    return (int(width * scale), int(height * scale))


def calculate_tolerance_ru(
    element_size: tuple[int, int],
    image_size: tuple[int, int],
    scale: float = 0.7,
) -> tuple[int, int]:
    """Calculate normalized tolerance for an element.

    This is a convenience function combining bounds_to_tolerance and tolerance_to_ru.
    The default scale of 0.7 means clicks within 70% of the element size are accepted.

    Args:
        element_size: (width, height) of the clickable element in pixels
        image_size: (width, height) of the full image in pixels
        scale: Fraction of element size to use as tolerance (default 0.7 = 70%)

    Returns:
        Tolerance in RU units [0, 1000]

    Example:
        >>> calculate_tolerance_ru((100, 50), (1920, 1080), scale=0.7)
        (36, 32)
    """
    pixel_tol = (int(element_size[0] * scale), int(element_size[1] * scale))
    return tolerance_to_ru(pixel_tol, image_size)
