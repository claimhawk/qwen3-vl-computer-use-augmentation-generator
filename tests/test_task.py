# Copyright (c) 2025 Tylt LLC. All rights reserved.
"""Tests for task.py classes."""

import random
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from cudag.core.task import BaseTask, EvalCase, TaskContext, TaskSample
from cudag.prompts.tools import ToolCall


class TestTaskSample:
    """Tests for TaskSample dataclass."""

    def test_creation(self) -> None:
        sample = TaskSample(
            id="test_00001",
            image_path=Path("/tmp/test.png"),
            human_prompt="Click the button",
            tool_call=ToolCall.left_click((500, 300)),
            pixel_coords=(500, 300),
            image_size=(1000, 1000),
        )
        assert sample.id == "test_00001"
        assert sample.human_prompt == "Click the button"
        assert sample.pixel_coords == (500, 300)

    def test_default_metadata(self) -> None:
        sample = TaskSample(
            id="test",
            image_path=Path("/tmp/test.png"),
            human_prompt="Test",
            tool_call=ToolCall.left_click((0, 0)),
            pixel_coords=(0, 0),
        )
        assert sample.metadata == {}

    def test_default_image_size(self) -> None:
        sample = TaskSample(
            id="test",
            image_path=Path("/tmp/test.png"),
            human_prompt="Test",
            tool_call=ToolCall.left_click((0, 0)),
            pixel_coords=(0, 0),
        )
        assert sample.image_size == (1000, 1000)

    def test_custom_metadata(self) -> None:
        sample = TaskSample(
            id="test",
            image_path=Path("/tmp/test.png"),
            human_prompt="Test",
            tool_call=ToolCall.left_click((0, 0)),
            pixel_coords=(0, 0),
            metadata={"task_type": "click-day", "target_date": "2025-01-15"},
        )
        assert sample.metadata["task_type"] == "click-day"
        assert sample.metadata["target_date"] == "2025-01-15"


class TestEvalCase:
    """Tests for EvalCase dataclass."""

    def test_creation(self) -> None:
        eval_case = EvalCase(
            eval_id="eval_001",
            screenshot=Path("/tmp/eval.png"),
            prompt="Click the submit button",
            expected_action={"name": "computer_use", "arguments": {"action": "left_click"}},
            tolerance=10,
        )
        assert eval_case.eval_id == "eval_001"
        assert eval_case.tolerance == 10

    def test_default_metadata(self) -> None:
        eval_case = EvalCase(
            eval_id="eval",
            screenshot=Path("/tmp/eval.png"),
            prompt="Test",
            expected_action={},
            tolerance=5,
        )
        assert eval_case.metadata == {}

    def test_pixel_coords_optional(self) -> None:
        eval_case = EvalCase(
            eval_id="eval",
            screenshot=Path("/tmp/eval.png"),
            prompt="Test",
            expected_action={},
            tolerance=5,
        )
        assert eval_case.pixel_coords is None


class TestTaskContext:
    """Tests for TaskContext dataclass."""

    def test_creation(self) -> None:
        rng = random.Random(42)
        ctx = TaskContext(
            rng=rng,
            index=5,
            output_dir=Path("/tmp/output"),
            config={"min_rows": 10},
            dataset_name="test-dataset",
        )
        assert ctx.index == 5
        assert ctx.dataset_name == "test-dataset"
        assert ctx.config["min_rows"] == 10

    def test_rng_is_seeded(self) -> None:
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        ctx1 = TaskContext(
            rng=rng1,
            index=0,
            output_dir=Path("/tmp"),
            config={},
            dataset_name="test",
        )
        ctx2 = TaskContext(
            rng=rng2,
            index=0,
            output_dir=Path("/tmp"),
            config={},
            dataset_name="test",
        )
        # Same seed should produce same random values
        assert ctx1.rng.randint(0, 1000) == ctx2.rng.randint(0, 1000)


class TestBaseTask:
    """Tests for BaseTask abstract class."""

    def test_subclass_implementation(self) -> None:
        # Create a mock renderer
        mock_renderer = MagicMock()
        mock_renderer.screen_class.meta.return_value.size = (1000, 1000)

        class TestTask(BaseTask):
            task_type = "test-task"

            def generate_sample(self, ctx: TaskContext) -> TaskSample:
                return TaskSample(
                    id=self.build_id(ctx),
                    image_path=Path("/tmp/test.png"),
                    human_prompt="Test prompt",
                    tool_call=ToolCall.left_click((500, 300)),
                    pixel_coords=(500, 300),
                )

            def generate_eval(self, ctx: TaskContext) -> EvalCase:
                return EvalCase(
                    eval_id=f"eval_{ctx.index}",
                    screenshot=Path("/tmp/eval.png"),
                    prompt="Test",
                    expected_action={},
                    tolerance=10,
                )

        task = TestTask(config={"key": "value"}, renderer=mock_renderer)
        assert task.task_type == "test-task"
        assert task.config == {"key": "value"}

    def test_build_id(self) -> None:
        mock_renderer = MagicMock()

        class TestTask(BaseTask):
            task_type = "test"

            def generate_sample(self, ctx: TaskContext) -> TaskSample:
                return TaskSample(
                    id=self.build_id(ctx),
                    image_path=Path("/tmp/test.png"),
                    human_prompt="Test",
                    tool_call=ToolCall.left_click((0, 0)),
                    pixel_coords=(0, 0),
                )

            def generate_eval(self, ctx: TaskContext) -> EvalCase:
                return EvalCase(
                    eval_id="eval",
                    screenshot=Path("/tmp/eval.png"),
                    prompt="Test",
                    expected_action={},
                    tolerance=10,
                )

        task = TestTask(config={}, renderer=mock_renderer)
        ctx = TaskContext(
            rng=random.Random(42),
            index=42,
            output_dir=Path("/tmp"),
            config={},
            dataset_name="my-dataset",
        )

        assert task.build_id(ctx) == "my-dataset_00042"
        assert task.build_id(ctx, suffix="_scroll") == "my-dataset_00042_scroll"

    def test_save_image_creates_directory(self) -> None:
        mock_renderer = MagicMock()
        mock_image = MagicMock()

        class TestTask(BaseTask):
            task_type = "test"

            def generate_sample(self, ctx: TaskContext) -> TaskSample:
                path = self.save_image(mock_image, ctx)
                return TaskSample(
                    id="test",
                    image_path=path,
                    human_prompt="Test",
                    tool_call=ToolCall.left_click((0, 0)),
                    pixel_coords=(0, 0),
                )

            def generate_eval(self, ctx: TaskContext) -> EvalCase:
                return EvalCase(
                    eval_id="eval",
                    screenshot=Path("/tmp/eval.png"),
                    prompt="Test",
                    expected_action={},
                    tolerance=10,
                )

        with tempfile.TemporaryDirectory() as tmpdir:
            task = TestTask(config={}, renderer=mock_renderer)
            ctx = TaskContext(
                rng=random.Random(42),
                index=0,
                output_dir=Path(tmpdir),
                config={},
                dataset_name="test",
            )

            path = task.save_image(mock_image, ctx)
            assert (Path(tmpdir) / "images").is_dir()
            assert path.suffix == ".png"
            mock_image.save.assert_called_once()

    def test_save_image_jpg(self) -> None:
        mock_renderer = MagicMock()
        mock_image = MagicMock()

        class TestTask(BaseTask):
            task_type = "test"

            def generate_sample(self, ctx: TaskContext) -> TaskSample:
                return TaskSample(
                    id="test",
                    image_path=Path("/tmp/test.png"),
                    human_prompt="Test",
                    tool_call=ToolCall.left_click((0, 0)),
                    pixel_coords=(0, 0),
                )

            def generate_eval(self, ctx: TaskContext) -> EvalCase:
                return EvalCase(
                    eval_id="eval",
                    screenshot=Path("/tmp/eval.png"),
                    prompt="Test",
                    expected_action={},
                    tolerance=10,
                )

        with tempfile.TemporaryDirectory() as tmpdir:
            task = TestTask(config={}, renderer=mock_renderer)
            ctx = TaskContext(
                rng=random.Random(42),
                index=5,
                output_dir=Path(tmpdir),
                config={},
                dataset_name="test",
            )

            path = task.save_image(mock_image, ctx, extension="jpg", quality=85)
            assert path.suffix == ".jpg"
            assert path.name == "test_00005.jpg"
            mock_image.save.assert_called_with(path, quality=85)

    def test_format_gpt_response(self) -> None:
        mock_renderer = MagicMock()

        class TestTask(BaseTask):
            task_type = "test"

            def generate_sample(self, ctx: TaskContext) -> TaskSample:
                return TaskSample(
                    id="test",
                    image_path=Path("/tmp/test.png"),
                    human_prompt="Test",
                    tool_call=ToolCall.left_click((0, 0)),
                    pixel_coords=(0, 0),
                )

            def generate_eval(self, ctx: TaskContext) -> EvalCase:
                return EvalCase(
                    eval_id="eval",
                    screenshot=Path("/tmp/eval.png"),
                    prompt="Test",
                    expected_action={},
                    tolerance=10,
                )

        task = TestTask(config={}, renderer=mock_renderer)
        tc = ToolCall.left_click((500, 300))
        response = task.format_gpt_response(tc)

        assert "<tool_call>" in response
        assert "</tool_call>" in response
        assert "left_click" in response
