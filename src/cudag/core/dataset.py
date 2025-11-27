# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Derivative works may be released by researchers,
# but original files may not be redistributed or used beyond research purposes.

"""Dataset builder for orchestrating sample generation.

The DatasetBuilder coordinates Screen, State, Renderer, and Tasks
to produce JSONL training datasets.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from cudag.core.coords import normalize_coord
from cudag.core.task import BaseTask, TaskContext, TaskSample, TestCase
from cudag.prompts.tools import format_tool_call


@dataclass
class DatasetConfig:
    """Configuration for dataset generation."""

    name_prefix: str
    """Prefix for dataset name (e.g., "calendar-mike")."""

    seed: int = 42
    """Random seed for reproducibility."""

    task_counts: dict[str, int] = field(default_factory=dict)
    """Number of samples per task type."""

    train_split: float = 0.8
    """Fraction of data for training (rest is test/val)."""

    system_prompt: str = "compact"
    """System prompt style: "osworld", "compact", or custom."""

    output_dir: Path | None = None
    """Output directory (auto-generated if None)."""

    image_format: str = "png"
    """Image format: "png" or "jpg"."""

    image_quality: int = 95
    """JPEG quality (ignored for PNG)."""

    held_out_enabled: bool = False
    """Whether to hold out samples for evaluation."""

    held_out_ratio: float = 0.1
    """Fraction of samples to hold out."""

    test_count: int = 100
    """Number of test cases to generate."""

    test_tolerance: tuple[int, int] = (10, 10)
    """Coordinate tolerance for test (x, y in RU units)."""

    annotation_ratio: float = 0.1
    """Fraction of test cases to annotate (0.0-1.0)."""

    annotation_enabled: bool = True
    """Whether to generate annotated test images."""

    def __post_init__(self) -> None:
        """Set default output directory if not provided."""
        if self.output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = Path("datasets") / f"{self.name_prefix}_{timestamp}"

    @classmethod
    def from_yaml(cls, path: Path) -> DatasetConfig:
        """Load config from YAML file."""
        import yaml

        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(
            name_prefix=data.get("name_prefix", "dataset"),
            seed=data.get("seed", 42),
            task_counts=data.get("tasks", {}),
            train_split=data.get("splits", {}).get("train", 0.8),
            system_prompt=data.get("system_prompt", "compact"),
            output_dir=Path(data["output_dir"]) if "output_dir" in data else None,
            image_format=data.get("output", {}).get("image_format", "png"),
            image_quality=data.get("output", {}).get("image_quality", 95),
            held_out_enabled=data.get("held_out", {}).get("enabled", False),
            held_out_ratio=data.get("held_out", {}).get("ratio", 0.1),
            test_count=data.get("test", {}).get("count", 100),
            test_tolerance=_parse_tolerance(data.get("test", {}).get("tolerance", [10, 10])),
            annotation_ratio=data.get("annotation", {}).get("ratio", 0.1),
            annotation_enabled=data.get("annotation", {}).get("enabled", True),
        )


def _parse_tolerance(value: int | list[int]) -> tuple[int, int]:
    """Parse tolerance from config - handles both int and [x, y] formats."""
    if isinstance(value, int):
        return (value, value)
    return tuple(value)  # type: ignore[return-value]


def annotate_test_image(
    image_path: Path,
    action: str,
    pixel_coords: tuple[int, int],
    prompt: str,
    output_path: Path | None = None,
) -> Path:
    """Annotate a test image with action, coordinates, and prompt.

    Draws:
    - Red crosshair at the click location
    - Action label near the click point
    - Extends canvas with white bar at bottom for prompt text

    Args:
        image_path: Path to the original test image.
        action: The action type (e.g., "left_click").
        pixel_coords: The (x, y) pixel coordinates of the action.
        prompt: The user prompt text to display.
        output_path: Where to save the annotated image. If None, saves
                     to same directory with "_annotated" suffix.

    Returns:
        Path to the annotated image.
    """
    from PIL import Image, ImageDraw, ImageFont

    # Load original image
    original = Image.open(image_path).convert("RGB")
    orig_width, orig_height = original.size

    # Create new canvas with extra height for prompt bar
    bar_height = 28
    new_height = orig_height + bar_height
    img = Image.new("RGB", (orig_width, new_height), (255, 255, 255))

    # Paste original image at top
    img.paste(original, (0, 0))

    draw = ImageDraw.Draw(img)
    x, y = pixel_coords

    # Draw crosshair at click location
    crosshair_size = 10
    crosshair_color = (255, 0, 0)  # Red
    # Horizontal line
    draw.line([(x - crosshair_size, y), (x + crosshair_size, y)], fill=crosshair_color, width=2)
    # Vertical line
    draw.line([(x, y - crosshair_size), (x, y + crosshair_size)], fill=crosshair_color, width=2)
    # Circle around crosshair
    draw.ellipse(
        [(x - crosshair_size, y - crosshair_size), (x + crosshair_size, y + crosshair_size)],
        outline=crosshair_color,
        width=2,
    )

    # Try to load a font, fall back to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        prompt_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except (OSError, IOError):
        font = ImageFont.load_default()
        prompt_font = font

    # Draw action label near click point
    action_text = f"{action} ({x}, {y})"
    label_x = min(x + crosshair_size + 5, orig_width - 100)
    label_y = max(y - 8, 5)

    # Background for label
    bbox = draw.textbbox((label_x, label_y), action_text, font=font)
    draw.rectangle([bbox[0] - 2, bbox[1] - 2, bbox[2] + 2, bbox[3] + 2], fill=(255, 255, 255))
    draw.text((label_x, label_y), action_text, fill=(255, 0, 0), font=font)

    # Draw prompt text in the extended area below the original image
    prompt_y = orig_height + 6
    draw.text((5, prompt_y), f"Prompt: {prompt}", fill=(0, 0, 0), font=prompt_font)

    # Determine output path
    if output_path is None:
        stem = image_path.stem
        output_path = image_path.parent / f"{stem}_annotated{image_path.suffix}"

    img.save(output_path)
    return output_path


class DatasetBuilder:
    """Orchestrates dataset generation from tasks.

    Example:
        builder = DatasetBuilder(
            config=DatasetConfig(name_prefix="calendar", task_counts={"click-day": 1000}),
            tasks=[ClickDayTask(config, renderer)],
        )
        builder.build()
    """

    def __init__(
        self,
        config: DatasetConfig,
        tasks: list[BaseTask],
    ) -> None:
        """Initialize the builder.

        Args:
            config: Dataset configuration
            tasks: List of task instances to generate from
        """
        self.config = config
        self.tasks = {t.task_type: t for t in tasks}
        self.rng = random.Random(config.seed)

    def build(self) -> Path:
        """Generate the complete dataset.

        Returns:
            Path to the output directory
        """
        output_dir = self.config.output_dir
        assert output_dir is not None

        # Create directories
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "images").mkdir(exist_ok=True)

        # Generate samples
        samples: list[dict[str, Any]] = []
        held_out: list[dict[str, Any]] = []
        index = 0

        for task_type, count in self.config.task_counts.items():
            if task_type not in self.tasks:
                raise ValueError(f"Unknown task type: {task_type}")

            task = self.tasks[task_type]
            for _ in range(count):
                ctx = TaskContext(
                    rng=self.rng,
                    index=index,
                    output_dir=output_dir,
                    config=task.config,
                    dataset_name=self.config.name_prefix,
                )

                # Use generate_samples() for 1:N image-to-samples pattern
                # A single render can produce multiple training samples
                task_samples = task.generate_samples(ctx)
                for sample in task_samples:
                    record = self._to_record(sample)

                    # Decide if this should be held out
                    if self.config.held_out_enabled and self.rng.random() < self.config.held_out_ratio:
                        held_out.append(record)
                    else:
                        samples.append(record)

                index += 1

        # Write data files
        self._write_jsonl(output_dir / "data.jsonl", samples + held_out)
        self._write_splits(output_dir, samples)

        if held_out:
            self._write_jsonl(output_dir / "held_out.jsonl", held_out)

        # Write config for reference
        self._write_config(output_dir)

        print(f"Generated {len(samples)} training samples, {len(held_out)} held out")
        print(f"Output: {output_dir}")

        return output_dir

    def _to_record(self, sample: TaskSample) -> dict[str, Any]:
        """Convert TaskSample to JSONL record."""
        # Get normalized coordinates
        norm_coord = normalize_coord(sample.pixel_coords, sample.image_size)

        # Update tool call with normalized coordinates
        tool_call = sample.tool_call.to_dict()
        if "coordinate" in tool_call["arguments"]:
            tool_call["arguments"]["coordinate"] = list(norm_coord)

        # Format GPT response
        gpt_value = format_tool_call(tool_call)

        # Build relative image path
        assert self.config.output_dir is not None
        image_rel = str(sample.image_path.relative_to(self.config.output_dir))

        return {
            "id": sample.id,
            "image": image_rel,
            "conversations": [
                {"from": "human", "value": f"<image>\n{sample.human_prompt}"},
                {"from": "gpt", "value": gpt_value},
            ],
            "metadata": {
                "task_type": sample.metadata.get("task_type", "unknown"),
                "real_coords": list(sample.pixel_coords),
                **{k: v for k, v in sample.metadata.items() if k != "task_type"},
            },
        }

    def _write_jsonl(self, path: Path, records: list[dict[str, Any]]) -> None:
        """Write records to JSONL file."""
        with open(path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")

    def _write_splits(self, output_dir: Path, samples: list[dict[str, Any]]) -> None:
        """Split samples and write train/val files."""
        # Shuffle for splitting
        shuffled = samples.copy()
        self.rng.shuffle(shuffled)

        split_idx = int(len(shuffled) * self.config.train_split)
        train = shuffled[:split_idx]
        val = shuffled[split_idx:]

        self._write_jsonl(output_dir / "train.jsonl", train)
        self._write_jsonl(output_dir / "val.jsonl", val)

        print(f"Split: {len(train)} train, {len(val)} val")

    def _write_config(self, output_dir: Path) -> None:
        """Write generation config for reference."""
        config_data = {
            "name_prefix": self.config.name_prefix,
            "seed": self.config.seed,
            "task_counts": self.config.task_counts,
            "train_split": self.config.train_split,
            "system_prompt": self.config.system_prompt,
            "generated_at": datetime.now().isoformat(),
        }
        with open(output_dir / "config.json", "w") as f:
            json.dump(config_data, f, indent=2)

    def build_tests(self) -> Path:
        """Generate test cases.

        Returns:
            Path to the test directory
        """
        output_dir = self.config.output_dir
        assert output_dir is not None

        # Create test directory structure (test/images/)
        test_dir = output_dir / "test"
        test_dir.mkdir(parents=True, exist_ok=True)
        (test_dir / "images").mkdir(exist_ok=True)

        # Create annotated directory if annotations enabled
        annotated_dir = test_dir / "annotated"
        if self.config.annotation_enabled:
            annotated_dir.mkdir(exist_ok=True)

        # Generate test cases - stop when we reach test_count
        test_cases: list[dict[str, Any]] = []
        raw_test_cases: list[TestCase] = []
        index = 0

        # Get task types to iterate through
        task_types = [t for t in self.config.task_counts.keys() if t in self.tasks]
        if not task_types:
            return test_dir

        # Keep generating until we have enough tests
        task_idx = 0
        while len(test_cases) < self.config.test_count:
            task_type = task_types[task_idx % len(task_types)]
            task = self.tasks[task_type]

            # Pass test_dir as output_dir so images save to test/images/
            ctx = TaskContext(
                rng=self.rng,
                index=index,
                output_dir=test_dir,
                config=task.config,
                dataset_name=self.config.name_prefix,
            )

            # Generate tests (can be 1:N from one image)
            tests = task.generate_tests(ctx)
            for test_case in tests:
                if len(test_cases) >= self.config.test_count:
                    break
                record = self._test_to_record(test_case, test_dir)
                test_cases.append(record)
                raw_test_cases.append(test_case)

            index += 1
            task_idx += 1

        # Generate annotations for a sample of test cases
        annotated_count = 0
        if self.config.annotation_enabled and self.config.annotation_ratio > 0:
            annotation_count = max(1, int(len(test_cases) * self.config.annotation_ratio))
            # Select indices to annotate (evenly distributed)
            indices_to_annotate = set(
                range(0, len(test_cases), max(1, len(test_cases) // annotation_count))
            )

            for idx in indices_to_annotate:
                if idx >= len(raw_test_cases):
                    continue
                test_case = raw_test_cases[idx]
                record = test_cases[idx]

                # Get action and coordinates
                action = test_case.expected_action.get("arguments", {}).get("action", "click")
                pixel_coords = test_case.pixel_coords or (0, 0)

                # Generate annotated image
                annotated_path = annotated_dir / f"{test_case.test_id}_annotated.png"
                annotate_test_image(
                    image_path=test_case.screenshot,
                    action=action,
                    pixel_coords=pixel_coords,
                    prompt=test_case.prompt,
                    output_path=annotated_path,
                )
                annotated_count += 1

        # Write test.json
        with open(test_dir / "test.json", "w", encoding="utf-8") as f:
            json.dump(test_cases, f, indent=2)

        if annotated_count > 0:
            print(f"Generated {len(test_cases)} test cases ({annotated_count} annotated)")
        else:
            print(f"Generated {len(test_cases)} test cases")

        return test_dir

    def _test_to_record(self, test_case: TestCase, test_dir: Path) -> dict[str, Any]:
        """Convert TestCase to record for test.json."""
        # Get image size from metadata if available, default to 1920x1080
        image_size = test_case.metadata.get("image_size", (1920, 1080))

        # Normalize coordinates in expected_action
        expected_action = test_case.expected_action.copy()
        if "arguments" in expected_action and "coordinate" in expected_action["arguments"]:
            pixel_coords = expected_action["arguments"]["coordinate"]
            if test_case.pixel_coords:
                pixel_coords = test_case.pixel_coords
            norm_coord = normalize_coord(tuple(pixel_coords), image_size)
            expected_action["arguments"]["coordinate"] = list(norm_coord)

        # Build relative screenshot path (relative to test_dir)
        screenshot_rel = str(test_case.screenshot.relative_to(test_dir))

        # Tolerance can come from test_case directly or from metadata
        # Convert to list for JSON serialization
        tolerance = test_case.tolerance
        if isinstance(tolerance, tuple):
            tolerance = list(tolerance)
        elif isinstance(tolerance, int):
            tolerance = [tolerance, tolerance]

        return {
            "test_id": test_case.test_id,
            "screenshot": screenshot_rel,
            "prompt": test_case.prompt,
            "expected_action": expected_action,
            "tolerance": tolerance,
            "metadata": {
                "real_coords": list(test_case.pixel_coords) if test_case.pixel_coords else None,
                **test_case.metadata,
            },
        }
