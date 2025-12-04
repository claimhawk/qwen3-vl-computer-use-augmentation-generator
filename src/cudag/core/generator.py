# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Derivative works may be released by researchers,
# but original files may not be redistributed or used beyond research purposes.

"""Generator entry point helper for CUDAG projects.

This module provides a standard entry point for dataset generation that
handles boilerplate like argument parsing, config loading, and dataset naming.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from cudag.core.dataset import DatasetBuilder, DatasetConfig
from cudag.core.utils import check_script_invocation, get_researcher_name

if TYPE_CHECKING:
    from cudag.core.renderer import BaseRenderer
    from cudag.core.task import BaseTask


def run_generator(
    renderer: BaseRenderer[Any],
    tasks: list[BaseTask],
    *,
    config_path: Path | str = "config/dataset.yaml",
    description: str = "Generate training dataset",
    extra_args: list[tuple[str, dict[str, Any]]] | None = None,
    config_modifier: Callable[[DatasetConfig, argparse.Namespace], None] | None = None,
    post_build: Callable[[Path, BaseRenderer[Any]], None] | None = None,
) -> Path:
    """Standard dataset generation entry point.

    Handles common boilerplate:
    - Script invocation check (warning if not run via ./scripts/generate.sh)
    - Argument parsing (--config, --seed, plus custom args)
    - Config loading from YAML
    - Dataset naming ({prefix}--{researcher}--{timestamp})
    - Dataset building and test generation

    Args:
        renderer: Initialized renderer instance for generating images.
        tasks: List of task instances to generate samples from.
        config_path: Default path to config YAML file. Defaults to
            "config/dataset.yaml".
        description: CLI description shown in --help. Defaults to
            "Generate training dataset".
        extra_args: Additional CLI arguments as list of (name, kwargs) tuples.
            Each tuple is passed to argparser.add_argument(name, **kwargs).
        config_modifier: Optional callback to modify config after loading.
            Called with (config, args) after config is loaded but before
            dataset name is generated. Use this to apply custom logic.
        post_build: Optional callback after dataset is built. Called with
            (output_dir, renderer). Use for debug images, validation, etc.

    Returns:
        Path to the generated dataset output directory.

    Example:
        Basic usage::

            from cudag import run_generator
            from .renderer import MyRenderer
            from .tasks import ClickTask, ScrollTask

            def main() -> None:
                renderer = MyRenderer(assets_dir=Path("assets"))
                tasks = [ClickTask(config={}, renderer=renderer)]
                run_generator(renderer, tasks)

        With custom arguments::

            def main() -> None:
                renderer = MyRenderer(assets_dir=Path("assets"))
                tasks = [ClickTask(config={}, renderer=renderer)]
                run_generator(
                    renderer,
                    tasks,
                    extra_args=[
                        ("--debug", {"action": "store_true", "help": "Enable debug"}),
                    ],
                )

        With config modification::

            def modify_config(config, args):
                if args.debug:
                    config.task_counts = {"click-day": 10}

            def main() -> None:
                renderer = MyRenderer(assets_dir=Path("assets"))
                tasks = [ClickTask(config={}, renderer=renderer)]
                run_generator(
                    renderer,
                    tasks,
                    config_modifier=modify_config,
                )
    """
    check_script_invocation()

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(config_path),
        help="Path to dataset config YAML",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override random seed from config",
    )

    # Add any extra arguments
    if extra_args:
        for name, kwargs in extra_args:
            parser.add_argument(name, **kwargs)

    args = parser.parse_args()

    # Load config
    config = DatasetConfig.from_yaml(args.config)
    if args.seed is not None:
        config.seed = args.seed

    # Allow custom config modification
    if config_modifier:
        config_modifier(config, args)

    # Build dataset name: {prefix}--{researcher}--{timestamp}
    # Using "--" delimiter to disambiguate from hyphens in expert names
    researcher = get_researcher_name()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_parts = [config.name_prefix]
    if researcher:
        name_parts.append(researcher)
    name_parts.append(timestamp)
    dataset_name = "--".join(name_parts)

    config.output_dir = Path("datasets") / dataset_name

    print(f"Loaded config: {config.name_prefix}")
    print(f"Tasks: {config.task_counts}")

    # Build dataset
    builder = DatasetBuilder(config=config, tasks=tasks)
    output_dir = builder.build()

    # Build tests
    builder.build_tests()

    # Optional post-build callback
    if post_build:
        post_build(output_dir, renderer)

    print(f"\nDataset generated at: {output_dir}")

    return output_dir
