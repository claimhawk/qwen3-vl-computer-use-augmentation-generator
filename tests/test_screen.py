# Copyright (c) 2025 Tylt LLC. All rights reserved.
"""Tests for screen.py DSL functions."""

import pytest

from cudag.core.screen import (
    Bounds,
    ButtonRegion,
    ClickRegion,
    DropdownRegion,
    GridRegion,
    Screen,
    ScrollRegion,
    button,
    dropdown,
    grid,
    region,
    scrollable,
)


class TestBounds:
    """Tests for Bounds dataclass."""

    def test_bounds_creation(self) -> None:
        b = Bounds(x=10, y=20, width=100, height=50)
        assert b.x == 10
        assert b.y == 20
        assert b.width == 100
        assert b.height == 50

    def test_bounds_center(self) -> None:
        b = Bounds(x=0, y=0, width=100, height=100)
        assert b.center == (50, 50)

        b2 = Bounds(x=100, y=200, width=50, height=30)
        assert b2.center == (125, 215)

    def test_bounds_right(self) -> None:
        b = Bounds(x=10, y=20, width=100, height=50)
        assert b.right == 110

    def test_bounds_bottom(self) -> None:
        b = Bounds(x=10, y=20, width=100, height=50)
        assert b.bottom == 70

    def test_bounds_contains(self) -> None:
        b = Bounds(x=0, y=0, width=100, height=100)
        assert b.contains((50, 50))
        assert b.contains((0, 0))
        assert b.contains((99, 99))
        assert not b.contains((100, 100))  # exclusive
        assert not b.contains((-1, 50))
        assert not b.contains((50, -1))

    def test_bounds_from_tuple(self) -> None:
        b = Bounds.from_tuple((10, 20, 100, 50))
        assert b.x == 10
        assert b.y == 20
        assert b.width == 100
        assert b.height == 50


class TestRegionDSL:
    """Tests for region() DSL function."""

    def test_region_creates_click_region(self) -> None:
        r = region((0, 0, 100, 50))
        assert isinstance(r, ClickRegion)
        assert r.bounds.x == 0
        assert r.bounds.width == 100

    def test_region_action_point(self) -> None:
        r = region((0, 0, 100, 100))
        assert r.get_action_point() == (50, 50)


class TestButtonDSL:
    """Tests for button() DSL function."""

    def test_button_basic(self) -> None:
        b = button((10, 20, 80, 30), label="Submit")
        assert isinstance(b, ButtonRegion)
        assert b.label == "Submit"
        assert b.bounds.x == 10

    def test_button_with_description(self) -> None:
        b = button((0, 0, 50, 25), label="Save", description="Save the form")
        assert b.description == "Save the form"

    def test_button_with_tolerance(self) -> None:
        b = button((0, 0, 50, 25), tolerance=(10, 10))
        assert b.tolerance == (10, 10)

    def test_button_action_point(self) -> None:
        b = button((100, 200, 50, 30))
        assert b.get_action_point() == (125, 215)


class TestGridDSL:
    """Tests for grid() DSL function."""

    def test_grid_basic(self) -> None:
        g = grid((0, 0, 700, 600), rows=6, cols=7)
        assert isinstance(g, GridRegion)
        assert g.rows == 6
        assert g.cols == 7

    def test_grid_cell_dimensions_auto(self) -> None:
        g = grid((0, 0, 700, 600), rows=6, cols=7)
        assert g.cell_width == 100  # 700 / 7
        assert g.cell_height == 100  # 600 / 6

    def test_grid_cell_dimensions_explicit(self) -> None:
        g = grid((0, 0, 700, 600), rows=6, cols=7, cell_width=50, cell_height=40)
        assert g.cell_width == 50
        assert g.cell_height == 40

    def test_grid_with_gaps(self) -> None:
        # 700 width, 7 cols, 6 gaps of 2px each = 700 - 12 = 688, 688/7 = 98
        g = grid((0, 0, 700, 600), rows=6, cols=7, row_gap=2, col_gap=2)
        assert g.col_gap == 2
        assert g.row_gap == 2

    def test_grid_action_point_center(self) -> None:
        g = grid((0, 0, 700, 600), rows=6, cols=7)
        # Center of entire grid
        assert g.get_action_point() == (350, 300)

    def test_grid_action_point_cell_tuple(self) -> None:
        g = grid((0, 0, 700, 600), rows=6, cols=7)
        # Cell (0, 0) center: cell_width=100, cell_height=100
        # Center should be at (50, 50)
        assert g.get_action_point((0, 0)) == (50, 50)

        # Cell (1, 2) center: x = 2*100 + 50 = 250, y = 1*100 + 50 = 150
        assert g.get_action_point((1, 2)) == (250, 150)

    def test_grid_action_point_cell_index(self) -> None:
        g = grid((0, 0, 700, 600), rows=6, cols=7)
        # Index 0 = (0, 0)
        assert g.get_action_point(0) == (50, 50)
        # Index 7 = (1, 0)
        assert g.get_action_point(7) == (50, 150)
        # Index 9 = (1, 2)
        assert g.get_action_point(9) == (250, 150)

    def test_grid_cell_bounds(self) -> None:
        g = grid((100, 100, 700, 600), rows=6, cols=7)
        cb = g.cell_bounds(0, 0)
        assert cb.x == 100
        assert cb.y == 100
        assert cb.width == 100
        assert cb.height == 100

        cb2 = g.cell_bounds(1, 2)
        assert cb2.x == 300  # 100 + 2*100
        assert cb2.y == 200  # 100 + 1*100


class TestScrollableDSL:
    """Tests for scrollable() DSL function."""

    def test_scrollable_basic(self) -> None:
        s = scrollable((0, 0, 800, 600), step=100)
        assert isinstance(s, ScrollRegion)
        assert s.scroll_step == 100
        assert s.direction == "vertical"

    def test_scrollable_horizontal(self) -> None:
        s = scrollable((0, 0, 800, 600), step=50, direction="horizontal")
        assert s.direction == "horizontal"

    def test_scrollable_action_point(self) -> None:
        s = scrollable((0, 0, 800, 600))
        assert s.get_action_point() == (400, 300)

    def test_scrollable_scroll_pixels(self) -> None:
        s = scrollable((0, 0, 800, 600), step=150)
        assert s.get_scroll_pixels("down") == 150
        assert s.get_scroll_pixels("up") == -150
        assert s.get_scroll_pixels("right") == 150
        assert s.get_scroll_pixels("left") == -150


class TestDropdownDSL:
    """Tests for dropdown() DSL function."""

    def test_dropdown_basic(self) -> None:
        d = dropdown((100, 50, 150, 25), items=["A", "B", "C"])
        assert isinstance(d, DropdownRegion)
        assert list(d.items) == ["A", "B", "C"]

    def test_dropdown_action_point_trigger(self) -> None:
        d = dropdown((100, 50, 150, 25))
        # Without target, returns center of dropdown trigger
        assert d.get_action_point() == (175, 62)  # 100+75, 50+12

    def test_dropdown_action_point_item_by_name(self) -> None:
        d = dropdown((100, 50, 150, 25), items=["A", "B", "C"], item_height=20)
        # Item "A" is index 0, below the dropdown
        # x = center x = 175
        # y = bottom (75) + 0*20 + 10 = 85
        assert d.get_action_point("A") == (175, 85)
        # Item "B" is index 1
        # y = 75 + 1*20 + 10 = 105
        assert d.get_action_point("B") == (175, 105)

    def test_dropdown_action_point_item_by_index(self) -> None:
        d = dropdown((100, 50, 150, 25), items=["A", "B", "C"], item_height=20)
        assert d.get_action_point(0) == (175, 85)
        assert d.get_action_point(2) == (175, 125)

    def test_dropdown_unknown_item(self) -> None:
        d = dropdown((100, 50, 150, 25), items=["A", "B"])
        # Unknown item returns center
        assert d.get_action_point("Z") == d.bounds.center


class TestScreen:
    """Tests for Screen base class."""

    def test_screen_subclass_collects_regions(self) -> None:
        class TestScreen(Screen):
            name = "test"
            base_image = "test.png"
            size = (800, 600)

            header = region((0, 0, 800, 50))
            submit = button((350, 500, 100, 40), label="Submit")

            def render(self, state):
                raise NotImplementedError

        assert "header" in TestScreen._regions
        assert "submit" in TestScreen._regions
        assert isinstance(TestScreen._regions["header"], ClickRegion)
        assert isinstance(TestScreen._regions["submit"], ButtonRegion)

    def test_screen_meta(self) -> None:
        class MyScreen(Screen):
            name = "my-screen"
            base_image = "base.png"
            size = (1024, 768)

            def render(self, state):
                raise NotImplementedError

        meta = MyScreen.meta()
        assert meta.name == "my-screen"
        assert meta.base_image == "base.png"
        assert meta.size == (1024, 768)

    def test_screen_get_region(self) -> None:
        class TestScreen(Screen):
            name = "test"
            btn = button((0, 0, 50, 25), label="Click")

            def render(self, state):
                raise NotImplementedError

        r = TestScreen.get_region("btn")
        assert isinstance(r, ButtonRegion)
        assert r.label == "Click"

    def test_screen_get_region_not_found(self) -> None:
        class TestScreen(Screen):
            name = "test"

            def render(self, state):
                raise NotImplementedError

        with pytest.raises(KeyError):
            TestScreen.get_region("nonexistent")

    def test_screen_regions_returns_copy(self) -> None:
        class TestScreen(Screen):
            name = "test"
            btn = button((0, 0, 50, 25))

            def render(self, state):
                raise NotImplementedError

        regions1 = TestScreen.regions()
        regions2 = TestScreen.regions()
        assert regions1 is not regions2

    def test_screen_default_name_from_class(self) -> None:
        class MyCustomScreen(Screen):
            base_image = "test.png"
            size = (100, 100)

            def render(self, state):
                raise NotImplementedError

        # Name should be "mycustom" (lowercased, "screen" removed)
        assert MyCustomScreen.meta().name == "mycustom"

    def test_screen_region_names_assigned(self) -> None:
        class TestScreen(Screen):
            name = "test"
            my_button = button((0, 0, 50, 25))

            def render(self, state):
                raise NotImplementedError

        assert TestScreen._regions["my_button"].name == "my_button"
