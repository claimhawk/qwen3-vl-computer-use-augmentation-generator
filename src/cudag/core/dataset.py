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
from cudag.core.task import BaseTask, EvalCase, TaskContext, TaskSample
from cudag.prompts.system import get_system_prompt
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

    eval_count: int = 100
    """Number of eval cases to generate."""

    eval_tolerance: int = 10
    """Coordinate tolerance for eval (RU units)."""

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
            eval_count=data.get("evals", {}).get("count", 100),
            eval_tolerance=data.get("evals", {}).get("tolerance", 10),
        )


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
        self.system_prompt = get_system_prompt(config.system_prompt)

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
                {"from": "system", "value": self.system_prompt},
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

    def build_evals(self) -> Path:
        """Generate evaluation cases.

        Returns:
            Path to the evals directory
        """
        output_dir = self.config.output_dir
        assert output_dir is not None

        # Create evals directory structure (evals/images/)
        evals_dir = output_dir / "evals"
        evals_dir.mkdir(parents=True, exist_ok=True)
        (evals_dir / "images").mkdir(exist_ok=True)

        # Generate eval cases - stop when we reach eval_count
        eval_cases: list[dict[str, Any]] = []
        index = 0

        # Get task types to iterate through
        task_types = [t for t in self.config.task_counts.keys() if t in self.tasks]
        if not task_types:
            return evals_dir

        # Keep generating until we have enough evals
        task_idx = 0
        while len(eval_cases) < self.config.eval_count:
            task_type = task_types[task_idx % len(task_types)]
            task = self.tasks[task_type]

            # Pass evals_dir as output_dir so images save to evals/images/
            ctx = TaskContext(
                rng=self.rng,
                index=index,
                output_dir=evals_dir,
                config=task.config,
                dataset_name=self.config.name_prefix,
            )

            # Generate evals (can be 1:N from one image)
            evals = task.generate_evals(ctx)
            for eval_case in evals:
                if len(eval_cases) >= self.config.eval_count:
                    break
                record = self._eval_to_record(eval_case, evals_dir)
                eval_cases.append(record)

            index += 1
            task_idx += 1

        # Write evals.json (not jsonl) to match calendar structure
        with open(evals_dir / "evals.json", "w", encoding="utf-8") as f:
            json.dump(eval_cases, f, indent=2)
        print(f"Generated {len(eval_cases)} eval cases")

        return evals_dir

    def _eval_to_record(self, eval_case: EvalCase, evals_dir: Path) -> dict[str, Any]:
        """Convert EvalCase to record for evals.json."""
        # Get image size from metadata if available, default to 1920x1080
        image_size = eval_case.metadata.get("image_size", (1920, 1080))

        # Normalize coordinates in expected_action
        expected_action = eval_case.expected_action.copy()
        if "arguments" in expected_action and "coordinate" in expected_action["arguments"]:
            pixel_coords = expected_action["arguments"]["coordinate"]
            if eval_case.pixel_coords:
                pixel_coords = eval_case.pixel_coords
            norm_coord = normalize_coord(tuple(pixel_coords), image_size)
            expected_action["arguments"]["coordinate"] = list(norm_coord)

        # Build relative screenshot path (relative to evals_dir)
        screenshot_rel = str(eval_case.screenshot.relative_to(evals_dir))

        return {
            "eval_id": eval_case.eval_id,
            "screenshot": screenshot_rel,
            "prompt": eval_case.prompt,
            "expected_action": expected_action,
            "tolerance": eval_case.tolerance,
            "metadata": {
                "real_coords": list(eval_case.pixel_coords) if eval_case.pixel_coords else None,
                **eval_case.metadata,
            },
        }
