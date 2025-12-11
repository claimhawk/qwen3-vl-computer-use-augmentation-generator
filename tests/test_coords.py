# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Tests for coords.py coordinate utilities."""

import math

import pytest

from cudag.core.coords import (
    RU_MAX,
    clamp_coord,
    coord_distance,
    coord_within_tolerance,
    get_normalized_bounds,
    normalize_coord,
    pixel_from_normalized,
)


class TestNormalizeCoord:
    """Tests for normalize_coord function.

    Coordinates are normalized with independent axis scaling.
    Both X and Y axes map independently to [0, 1000], matching Qwen3-VL's
    coordinate system.
    """

    def test_normalize_center(self) -> None:
        # Center of 1000x1000 square image should be (500, 500)
        result = normalize_coord((500, 500), (1000, 1000))
        assert result == (500, 500)

    def test_normalize_origin(self) -> None:
        result = normalize_coord((0, 0), (1000, 1000))
        assert result == (0, 0)

    def test_normalize_max(self) -> None:
        result = normalize_coord((1000, 1000), (1000, 1000))
        assert result == (1000, 1000)

    def test_normalize_non_square_landscape(self) -> None:
        # 800x600 image (landscape) - independent scaling
        # x: 400/800*1000 = 500
        # y: 300/600*1000 = 500
        result = normalize_coord((400, 300), (800, 600))
        assert result == (500, 500)

    def test_normalize_non_square_portrait(self) -> None:
        # 600x800 image (portrait) - independent scaling
        # x: 300/600*1000 = 500
        # y: 400/800*1000 = 500
        result = normalize_coord((300, 400), (600, 800))
        assert result == (500, 500)

    def test_normalize_1920x1080(self) -> None:
        # 1920x1080 image (16:9) - independent scaling
        # x: 960/1920*1000 = 500
        # y: 540/1080*1000 = 500
        result = normalize_coord((960, 540), (1920, 1080))
        assert result == (500, 500)

    def test_normalize_rounds_correctly(self) -> None:
        # 1155x853 image (from claim window) - independent scaling
        # x: 577/1155*1000 = 499.6 -> 500
        # y: 300/853*1000 = 351.7 -> 352
        result = normalize_coord((577, 300), (1155, 853))
        assert result == (500, 352)

    def test_normalize_corner_cases(self) -> None:
        # Bottom-right corner of 1920x1080
        # x: 1920/1920*1000 = 1000
        # y: 1080/1080*1000 = 1000
        result = normalize_coord((1920, 1080), (1920, 1080))
        assert result == (1000, 1000)

    def test_normalize_invalid_size_raises(self) -> None:
        with pytest.raises(ValueError):
            normalize_coord((100, 100), (0, 100))
        with pytest.raises(ValueError):
            normalize_coord((100, 100), (100, 0))
        with pytest.raises(ValueError):
            normalize_coord((100, 100), (-100, 100))


class TestPixelFromNormalized:
    """Tests for pixel_from_normalized function."""

    def test_pixel_center(self) -> None:
        result = pixel_from_normalized((500, 500), (1000, 1000))
        assert result == (500, 500)

    def test_pixel_origin(self) -> None:
        result = pixel_from_normalized((0, 0), (1000, 1000))
        assert result == (0, 0)

    def test_pixel_max(self) -> None:
        result = pixel_from_normalized((1000, 1000), (1000, 1000))
        assert result == (1000, 1000)

    def test_pixel_non_square_landscape(self) -> None:
        # Normalized (500, 500) on 800x600 image - independent scaling
        # x: 500/1000*800 = 400
        # y: 500/1000*600 = 300
        result = pixel_from_normalized((500, 500), (800, 600))
        assert result == (400, 300)

    def test_pixel_non_square_portrait(self) -> None:
        # Normalized (500, 500) on 600x800 image - independent scaling
        # x: 500/1000*600 = 300
        # y: 500/1000*800 = 400
        result = pixel_from_normalized((500, 500), (600, 800))
        assert result == (300, 400)

    def test_pixel_1920x1080(self) -> None:
        # Normalized (500, 500) on 1920x1080 image
        # x: 500/1000*1920 = 960
        # y: 500/1000*1080 = 540
        result = pixel_from_normalized((500, 500), (1920, 1080))
        assert result == (960, 540)

    def test_pixel_invalid_size_raises(self) -> None:
        with pytest.raises(ValueError):
            pixel_from_normalized((500, 500), (0, 100))

    def test_roundtrip(self) -> None:
        """Test that normalize -> pixel gives back original (approximately)."""
        original = (577, 300)
        image_size = (1155, 853)
        normalized = normalize_coord(original, image_size)
        recovered = pixel_from_normalized(normalized, image_size)
        # Should be within 1 pixel due to rounding
        assert abs(recovered[0] - original[0]) <= 1
        assert abs(recovered[1] - original[1]) <= 1

    def test_roundtrip_1920x1080(self) -> None:
        """Test roundtrip for common screen size."""
        original = (960, 540)
        image_size = (1920, 1080)
        normalized = normalize_coord(original, image_size)
        recovered = pixel_from_normalized(normalized, image_size)
        assert abs(recovered[0] - original[0]) <= 1
        assert abs(recovered[1] - original[1]) <= 1


class TestGetNormalizedBounds:
    """Tests for get_normalized_bounds function.

    With independent axis scaling, both axes always map to [0, 1000].
    """

    def test_square_image(self) -> None:
        # 1000x1000 square -> (1000, 1000)
        result = get_normalized_bounds((1000, 1000))
        assert result == (1000, 1000)

    def test_landscape_image(self) -> None:
        # 1920x1080 (16:9 landscape) - both axes map to 1000
        result = get_normalized_bounds((1920, 1080))
        assert result == (1000, 1000)

    def test_portrait_image(self) -> None:
        # 1080x1920 (9:16 portrait) - both axes map to 1000
        result = get_normalized_bounds((1080, 1920))
        assert result == (1000, 1000)

    def test_800x600(self) -> None:
        # 800x600 (4:3 landscape) - both axes map to 1000
        result = get_normalized_bounds((800, 600))
        assert result == (1000, 1000)

    def test_invalid_size_raises(self) -> None:
        with pytest.raises(ValueError):
            get_normalized_bounds((0, 100))


class TestClampCoord:
    """Tests for clamp_coord function."""

    def test_clamp_within_range(self) -> None:
        result = clamp_coord((500, 500))
        assert result == (500, 500)

    def test_clamp_negative(self) -> None:
        result = clamp_coord((-10, -20))
        assert result == (0, 0)

    def test_clamp_over_max(self) -> None:
        result = clamp_coord((1500, 2000))
        assert result == (1000, 1000)

    def test_clamp_mixed(self) -> None:
        result = clamp_coord((-5, 1200))
        assert result == (0, 1000)

    def test_clamp_custom_max(self) -> None:
        result = clamp_coord((150, 50), max_val=100)
        assert result == (100, 50)


class TestCoordDistance:
    """Tests for coord_distance function."""

    def test_distance_same_point(self) -> None:
        result = coord_distance((100, 100), (100, 100))
        assert result == 0.0

    def test_distance_horizontal(self) -> None:
        result = coord_distance((0, 0), (100, 0))
        assert result == 100.0

    def test_distance_vertical(self) -> None:
        result = coord_distance((0, 0), (0, 100))
        assert result == 100.0

    def test_distance_diagonal(self) -> None:
        # 3-4-5 triangle
        result = coord_distance((0, 0), (3, 4))
        assert result == 5.0

    def test_distance_pythagorean(self) -> None:
        # sqrt(100^2 + 100^2) = sqrt(20000) ≈ 141.42
        result = coord_distance((0, 0), (100, 100))
        assert abs(result - math.sqrt(20000)) < 0.01


class TestCoordWithinTolerance:
    """Tests for coord_within_tolerance function."""

    def test_within_exact_match(self) -> None:
        assert coord_within_tolerance((100, 100), (100, 100), 0)

    def test_within_small_tolerance(self) -> None:
        assert coord_within_tolerance((100, 100), (103, 104), 10)

    def test_within_boundary(self) -> None:
        # Distance of 5, tolerance of 5 should pass
        assert coord_within_tolerance((0, 0), (3, 4), 5)

    def test_outside_tolerance(self) -> None:
        # Distance of 5, tolerance of 4 should fail
        assert not coord_within_tolerance((0, 0), (3, 4), 4)

    def test_large_tolerance(self) -> None:
        assert coord_within_tolerance((0, 0), (100, 100), 200)


class TestRuMax:
    """Tests for RU_MAX constant."""

    def test_ru_max_value(self) -> None:
        assert RU_MAX == 1000
