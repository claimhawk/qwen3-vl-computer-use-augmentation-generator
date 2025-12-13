# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

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
from typing import Any, Callable

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

    system_prompt: str = "computer-use"
    """System prompt style: "computer-use", "compact", or custom."""

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
    """Number of test cases to generate PER TASK TYPE."""

    test_distribution: dict[str, int] = field(default_factory=dict)
    """Per-task test counts. Overrides auto-distribution when set."""

    test_tolerance: tuple[int, int] = (10, 10)
    """Coordinate tolerance for test (x, y in RU units)."""

    annotation_ratio: float = 0.1
    """Fraction of test cases to annotate (0.0-1.0)."""

    annotation_enabled: bool = True
    """Whether to generate annotated test images."""

    annotation_per_type: dict[str, int] = field(default_factory=dict)
    """Number of annotations per task type. Overrides annotation_ratio when set."""

    task_distributions: dict[str, dict[str, float]] = field(default_factory=dict)
    """Distribution of sample types within each task type.

    Example:
        task_distributions:
          click-appointment:
            grey_grey: 0.80      # 80% grey background + grey status
            other_colors: 0.15  # 15% other color combos
            adversarial: 0.05   # 5% no match cases
          hover-appointment:
            grey_grey: 0.80
            other_colors: 0.15
            adversarial: 0.05
    """

    def __post_init__(self) -> None:
        """Set default output directory if not provided."""
        if self.output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = Path("datasets") / f"{self.name_prefix}_{timestamp}"

    def get_distribution(self, task_type: str) -> dict[str, float]:
        """Get distribution for a task type.

        Returns the task-specific distribution if defined, otherwise
        returns an empty dict (task should use its own defaults).
        """
        return self.task_distributions.get(task_type, {})

    def sample_distribution_type(self, task_type: str, rng: Any) -> str | None:
        """Sample a distribution type for a task.

        Args:
            task_type: The task type to sample for.
            rng: Random number generator.

        Returns:
            The sampled distribution type name, or None if no distribution defined.
        """
        dist = self.get_distribution(task_type)
        if not dist:
            return None

        roll = rng.random()
        cumulative = 0.0
        for dist_type, prob in dist.items():
            cumulative += prob
            if roll < cumulative:
                return dist_type
        # Return last type if we somehow miss due to float precision
        return list(dist.keys())[-1] if dist else None

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
            system_prompt=data.get("system_prompt", "computer-use"),
            output_dir=Path(data["output_dir"]) if "output_dir" in data else None,
            image_format=data.get("output", {}).get("image_format", "png"),
            image_quality=data.get("output", {}).get("image_quality", 95),
            held_out_enabled=data.get("held_out", {}).get("enabled", False),
            held_out_ratio=data.get("held_out", {}).get("ratio", 0.1),
            test_count=data.get("test", {}).get("count", 100),
            test_distribution=data.get("test", {}).get("distribution", {}),
            test_tolerance=_parse_tolerance(data.get("test", {}).get("tolerance", [10, 10])),
            annotation_ratio=data.get("annotation", {}).get("ratio", 0.1),
            annotation_enabled=data.get("annotation", {}).get("enabled", True),
            annotation_per_type=data.get("annotation", {}).get("per_type", {}),
            task_distributions=data.get("task_distributions", {}),
        )


def _parse_tolerance(value: int | list[int]) -> tuple[int, int]:
    """Parse tolerance from config - handles both int and [x, y] formats."""
    if isinstance(value, int):
        return (value, value)
    return tuple(value)  # type: ignore[return-value]


def _wrap_text(text: str, font: Any, max_width: int, draw: Any) -> list[str]:
    """Wrap text to fit within max_width pixels.

    Args:
        text: The text to wrap.
        font: PIL ImageFont to use for measuring.
        max_width: Maximum width in pixels.
        draw: PIL ImageDraw for measuring text.

    Returns:
        List of wrapped lines.
    """
    words = text.split()
    lines = []
    current_line: list[str] = []

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))

    return lines if lines else [""]


def annotate_test_image(
    image_path: Path,
    tool_calls: list[dict[str, Any]],
    pixel_coords: tuple[int, int],
    prompt: str,
    output_path: Path | None = None,
    bbox_pixels: tuple[int, int, int, int] | None = None,
) -> Path:
    """Annotate a test image with tool call output and prompt.

    Draws:
    - Red crosshair at the click location (for click/hover tasks)
    - Red bounding box rectangle (for grounding tasks with bbox_pixels)
    - Extends canvas with white bar at bottom for prompt and <tool_call> output

    Args:
        image_path: Path to the original test image.
        tool_calls: List of tool call dicts (from ToolCall.to_dict()).
        pixel_coords: The (x, y) pixel coordinates for crosshair.
        prompt: The user prompt text to display.
        output_path: Where to save the annotated image. If None, saves
                     to same directory with "_annotated" suffix.
        bbox_pixels: Optional bounding box as (x, y, width, height) in pixels.
                     If provided, draws a rectangle instead of crosshair.

    Returns:
        Path to the annotated image.
    """
    from PIL import Image, ImageDraw, ImageFont

    # Load original image
    original = Image.open(image_path).convert("RGB")
    orig_width, orig_height = original.size

    # Try to load a monospace font for JSON, fall back to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 11)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
        except (OSError, IOError):
            font = ImageFont.load_default()

    # Create temporary draw to measure text for wrapping
    temp_img = Image.new("RGB", (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)

    # Wrap the prompt text to fit image width (with margins)
    margin = 10
    max_text_width = orig_width - margin * 2
    prompt_text = f"Prompt: {prompt}"
    wrapped_prompt = _wrap_text(prompt_text, font, max_text_width, temp_draw)

    # Format tool calls as prettified JSON with <tool_call> tags
    tool_call_lines: list[str] = []
    for tc in tool_calls:
        tool_call_lines.append("<tool_call>")
        # Pretty print JSON with 2-space indent
        pretty_json = json.dumps(tc, indent=2)
        for json_line in pretty_json.split("\n"):
            tool_call_lines.append(json_line)
        tool_call_lines.append("</tool_call>")

    # Calculate bar height based on number of lines
    line_height = 14
    total_lines = len(wrapped_prompt) + len(tool_call_lines) + 1  # +1 for spacing
    bar_height = (total_lines * line_height) + 12  # +12 for padding

    # Create new canvas with extra height for prompt and tool call output
    new_height = orig_height + bar_height
    img = Image.new("RGB", (orig_width, new_height), (255, 255, 255))

    # Paste original image at top
    img.paste(original, (0, 0))

    draw = ImageDraw.Draw(img)
    annotation_color = (255, 0, 0)  # Red

    if bbox_pixels is not None:
        # Draw bounding box rectangle for grounding tasks
        bx, by, bw, bh = bbox_pixels
        draw.rectangle(
            [(bx, by), (bx + bw, by + bh)],
            outline=annotation_color,
            width=3,
        )
    else:
        # Draw crosshair at click location
        x, y = pixel_coords
        crosshair_size = 10
        # Horizontal line
        draw.line([(x - crosshair_size, y), (x + crosshair_size, y)], fill=annotation_color, width=2)
        # Vertical line
        draw.line([(x, y - crosshair_size), (x, y + crosshair_size)], fill=annotation_color, width=2)
        # Circle around crosshair
        draw.ellipse(
            [(x - crosshair_size, y - crosshair_size), (x + crosshair_size, y + crosshair_size)],
            outline=annotation_color,
            width=2,
        )

    # Draw wrapped prompt text in the extended area below the original image
    current_y = orig_height + 4
    for line in wrapped_prompt:
        draw.text((5, current_y), line, fill=(0, 0, 0), font=font)
        current_y += line_height

    # Add spacing
    current_y += 4

    # Draw tool call output (model response)
    for line in tool_call_lines:
        # Color the XML tags differently
        if line.startswith("<tool_call>") or line.startswith("</tool_call>"):
            draw.text((5, current_y), line, fill=(128, 0, 128), font=font)  # Purple for tags
        else:
            draw.text((5, current_y), line, fill=(0, 100, 0), font=font)  # Dark green for JSON
        current_y += line_height

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

    def build(
        self,
        start_index: int = 0,
        checkpoint_callback: Callable[[int], None] | None = None,
        checkpoint_interval: int = 1000,
    ) -> Path:
        """Generate the complete dataset.

        Args:
            start_index: Skip samples up to this index (for resume after preemption)
            checkpoint_callback: Called with sample count every checkpoint_interval samples
            checkpoint_interval: How often to call checkpoint_callback (default 1000)

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
        samples_generated = 0
        last_checkpoint = 0

        for task_type, count in self.config.task_counts.items():
            if task_type not in self.tasks:
                raise ValueError(f"Unknown task type: {task_type}")

            task = self.tasks[task_type]
            for _ in range(count):
                # Skip samples until we reach start_index
                if index < start_index:
                    index += 1
                    continue

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
                samples_generated += 1

                # Checkpoint callback
                if checkpoint_callback and samples_generated - last_checkpoint >= checkpoint_interval:
                    checkpoint_callback(samples_generated)
                    last_checkpoint = samples_generated

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

        # Check if sample has multiple tool_calls in metadata
        if "tool_calls" in sample.metadata and len(sample.metadata["tool_calls"]) > 1:
            # Format all tool calls for multi-action samples
            gpt_parts = []
            for tc in sample.metadata["tool_calls"]:
                gpt_parts.append(format_tool_call(tc))
            gpt_value = "\n".join(gpt_parts)
        else:
            # Single tool call - update with normalized coordinates
            tool_call = sample.tool_call.to_dict()
            if "coordinate" in tool_call["arguments"]:
                tool_call["arguments"]["coordinate"] = list(norm_coord)
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
        # Extract task_types from task_counts keys
        task_types = list(self.config.task_counts.keys())

        config_data = {
            "name_prefix": self.config.name_prefix,
            "seed": self.config.seed,
            "task_types": task_types,
            "task_counts": self.config.task_counts,
            "train_split": self.config.train_split,
            "system_prompt": self.config.system_prompt,
            "task_distributions": self.config.task_distributions,
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

        # Generate test_count tests PER task type
        for task_type in task_types:
            if task_type not in self.tasks:
                continue
            task = self.tasks[task_type]
            generated = 0

            while generated < self.config.test_count:
                ctx = TaskContext(
                    rng=self.rng,
                    index=index,
                    output_dir=test_dir,
                    config=task.config,
                    dataset_name=self.config.name_prefix,
                )
                tests = task.generate_tests(ctx)
                for test_case in tests:
                    if generated >= self.config.test_count:
                        break
                    record = self._test_to_record(test_case, test_dir)
                    test_cases.append(record)
                    raw_test_cases.append(test_case)
                    generated += 1
                index += 1

        # ALWAYS generate 1 annotation per task type for tests (regardless of config)
        # For grounding tasks, generate 1 annotation per unique element_label
        annotated_count = 0
        annotated_dir.mkdir(exist_ok=True)

        # Group indices by task type (and element_label for grounding)
        indices_by_key: dict[str, list[int]] = {}
        for idx, test_case in enumerate(raw_test_cases):
            task_type = test_case.metadata.get("task_type", "unknown")
            # For grounding tasks, use element_label as additional key
            if task_type == "grounding":
                element_label = test_case.metadata.get("element_label", "unknown")
                key = f"grounding:{element_label}"
            else:
                key = task_type
            if key not in indices_by_key:
                indices_by_key[key] = []
            indices_by_key[key].append(idx)

        # Select 1 index per key to annotate
        indices_to_annotate: set[int] = set()
        for key, indices in indices_by_key.items():
            if indices:
                indices_to_annotate.add(indices[0])

        for idx in sorted(indices_to_annotate):
            if idx >= len(raw_test_cases):
                continue
            test_case = raw_test_cases[idx]

            # Get pixel coordinates for crosshair
            pixel_coords = test_case.pixel_coords or (0, 0)

            # Build tool_calls list from expected_action and any additional actions
            tool_calls = [test_case.expected_action]

            # Check for additional tool calls in metadata (e.g., type action for textfields)
            if "additional_tool_calls" in test_case.metadata:
                tool_calls.extend(test_case.metadata["additional_tool_calls"])

            # Generate annotated image - include task type in filename
            task_type = test_case.metadata.get("task_type", "unknown")
            # For grounding, include element_label in filename
            if task_type == "grounding":
                element_label = test_case.metadata.get("element_label", "unknown")
                annotated_path = annotated_dir / f"{task_type}_{element_label}_{test_case.test_id}_annotated.png"
            else:
                annotated_path = annotated_dir / f"{task_type}_{test_case.test_id}_annotated.png"

            # Extract bbox_pixels for grounding tasks (format: [x, y, width, height])
            bbox_pixels = None
            if "bbox_pixels" in test_case.metadata:
                bp = test_case.metadata["bbox_pixels"]
                bbox_pixels = (bp[0], bp[1], bp[2], bp[3])

            annotate_test_image(
                image_path=test_case.screenshot,
                tool_calls=tool_calls,
                pixel_coords=pixel_coords,
                prompt=test_case.prompt,
                output_path=annotated_path,
                bbox_pixels=bbox_pixels,
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
