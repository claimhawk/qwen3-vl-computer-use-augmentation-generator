#!/usr/bin/env python3
# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Interactive dataset verification and configuration tool.

Usage:
    python scripts/verify.py --config config/dataset.yaml
    python scripts/verify.py --dataset datasets/my-dataset

Allows interactive modification of:
- Task counts (training samples per task type)
- Test distribution (tests per task type)
- Train/val split ratio
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml


def load_config(config_path: Path) -> dict:
    """Load dataset configuration from YAML."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def save_config(config_path: Path, config: dict) -> None:
    """Save dataset configuration to YAML."""
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def analyze_dataset(dataset_dir: Path) -> dict:
    """Analyze a generated dataset and return stats."""
    stats = {
        "dataset_dir": str(dataset_dir),
        "training": {},
        "tests": {},
        "images": 0,
    }

    # Count training samples by task type
    data_path = dataset_dir / "data.jsonl"
    if data_path.exists():
        task_counts: Counter[str] = Counter()
        with open(data_path) as f:
            for line in f:
                record = json.loads(line)
                task_type = record.get("metadata", {}).get("task_type", "unknown")
                task_counts[task_type] += 1
        stats["training"] = dict(task_counts)

    # Count training images
    images_dir = dataset_dir / "images"
    if images_dir.exists():
        stats["images"] = len(list(images_dir.glob("*")))

    # Count tests by task type
    test_json = dataset_dir / "test" / "test.json"
    if test_json.exists():
        with open(test_json) as f:
            tests = json.load(f)
        test_counts: Counter[str] = Counter()
        for test in tests:
            task_type = test.get("metadata", {}).get("task_type", "unknown")
            test_counts[task_type] += 1
        stats["tests"] = dict(test_counts)

    return stats


def print_stats(stats: dict, config: dict | None = None) -> None:
    """Print dataset statistics in a readable format."""
    print("\n" + "=" * 60)
    print("DATASET STATISTICS")
    print("=" * 60)

    if config:
        print(f"\nConfig: {config.get('name_prefix', 'unknown')}")
        print(f"Seed: {config.get('seed', 'N/A')}")

    print(f"\nDataset: {stats['dataset_dir']}")
    print(f"Total images: {stats['images']}")

    # Training samples
    print("\n--- TRAINING SAMPLES ---")
    training = stats.get("training", {})
    total_training = sum(training.values())
    print(f"Total: {total_training}")

    if training:
        max_name_len = max(len(name) for name in training.keys())
        for task_type, count in sorted(training.items()):
            pct = (count / total_training * 100) if total_training > 0 else 0
            bar = "#" * int(pct / 2)
            print(f"  {task_type:<{max_name_len}} : {count:>5} ({pct:5.1f}%) {bar}")

    # Test samples
    print("\n--- TEST SAMPLES ---")
    tests = stats.get("tests", {})
    total_tests = sum(tests.values())
    print(f"Total: {total_tests}")

    if tests:
        max_name_len = max(len(name) for name in tests.keys())
        for task_type, count in sorted(tests.items()):
            pct = (count / total_tests * 100) if total_tests > 0 else 0
            print(f"  {task_type:<{max_name_len}} : {count:>3} ({pct:5.1f}%)")

    print("=" * 60)


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Prompt user for yes/no answer."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        response = input(question + suffix).strip().lower()
        if not response:
            return default
        if response in ("y", "yes"):
            return True
        if response in ("n", "no"):
            return False
        print("Please answer 'y' or 'n'")


def prompt_int(question: str, default: int | None = None) -> int:
    """Prompt user for integer input."""
    suffix = f" [{default}]: " if default is not None else ": "
    while True:
        response = input(question + suffix).strip()
        if not response and default is not None:
            return default
        try:
            return int(response)
        except ValueError:
            print("Please enter a valid integer")


def edit_task_counts(config: dict) -> tuple[dict, bool]:
    """Interactive editor for task counts. Returns (config, changed)."""
    tasks = config.get("tasks", {})

    print("\n--- EDIT TASK COUNTS ---")
    print("Enter new count for each task type (press Enter to keep current):\n")

    new_tasks = {}
    for task_type, current_count in tasks.items():
        new_count = prompt_int(f"  {task_type}", default=current_count)
        new_tasks[task_type] = new_count

    # Check for new tasks
    if prompt_yes_no("\nAdd a new task type?", default=False):
        task_type = input("  Task type name: ").strip()
        count = prompt_int(f"  {task_type} count", default=100)
        new_tasks[task_type] = count

    changed = new_tasks != tasks
    config["tasks"] = new_tasks
    return config, changed


def calc_auto_test_distribution(task_types: list[str], total: int) -> dict[str, int]:
    """Calculate auto-distribution: 3 each for scroll/click, rest for select."""
    dist: dict[str, int] = {}
    simple_tasks = [t for t in task_types if t.startswith("scroll-") or t.startswith("click-")]
    select_tasks = [t for t in task_types if t.startswith("select-")]

    simple_per_task = 3
    simple_total = len(simple_tasks) * simple_per_task
    remaining = max(0, total - simple_total)

    for task_type in simple_tasks:
        dist[task_type] = simple_per_task

    if select_tasks and remaining > 0:
        per_select = remaining // len(select_tasks)
        remainder = remaining % len(select_tasks)
        for i, task_type in enumerate(select_tasks):
            dist[task_type] = per_select + (1 if i < remainder else 0)
    else:
        for task_type in select_tasks:
            dist[task_type] = 0

    return dist


def edit_test_distribution(config: dict) -> tuple[dict, bool]:
    """Interactive editor for test distribution. Returns (config, changed)."""
    test_config = config.get("test", {})
    total_tests = test_config.get("count", 100)
    current_dist = test_config.get("distribution", {})
    task_types = list(config.get("tasks", {}).keys())

    print("\n--- EDIT TEST DISTRIBUTION ---")
    new_total = prompt_int("Total test count", default=total_tests)

    # Calculate auto values for any tasks not explicitly set
    auto_dist = calc_auto_test_distribution(task_types, new_total)

    print("\nPer-task test counts (press Enter to keep current):")
    new_dist: dict[str, int] = {}
    for task_type in task_types:
        # Use explicit value if set, otherwise show auto-calculated
        current = current_dist.get(task_type, auto_dist.get(task_type, 0))
        new_count = prompt_int(f"  {task_type}", default=current)
        new_dist[task_type] = new_count

    # Check if anything changed
    changed = (new_total != total_tests) or (new_dist != current_dist)

    test_config["count"] = new_total
    test_config["distribution"] = new_dist

    config["test"] = test_config
    return config, changed


def run_generator(config_path: Path, verbose: bool = False) -> Path | None:
    """Run the generator and return the generated dataset path."""
    import os
    import threading
    import time

    print("\n" + "-" * 40)
    print("Running generator (this may take a few minutes)...")
    print("-" * 40 + "\n", flush=True)

    env = os.environ.copy()
    env["CUDAG_FROM_SCRIPT"] = "1"
    cmd = ["uv", "run", "python", "generator.py", "--config", str(config_path)]

    if verbose:
        # Stream output directly
        result = subprocess.run(cmd, env=env)
    else:
        # Spinner for progress indication
        stop_spinner = threading.Event()

        def spinner() -> None:
            chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            i = 0
            while not stop_spinner.is_set():
                print(f"\r{chars[i % len(chars)]} Generating...", end="", flush=True)
                time.sleep(0.1)
                i += 1
            print("\r" + " " * 20 + "\r", end="", flush=True)

        spinner_thread = threading.Thread(target=spinner)
        spinner_thread.start()

        result = subprocess.run(cmd, capture_output=True, text=True, env=env)

        stop_spinner.set()
        spinner_thread.join()

        if result.returncode == 0:
            print(result.stdout)
        else:
            print(result.stderr)

    if result.returncode != 0:
        print("ERROR: Generator failed!")
        return None

    # Find the generated dataset
    datasets_dir = Path("datasets")
    if datasets_dir.exists():
        datasets = sorted(datasets_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        if datasets:
            return datasets[0]

    return None


def find_latest_dataset() -> Path | None:
    """Find the most recently generated dataset."""
    datasets_dir = Path("datasets")
    if not datasets_dir.exists():
        return None
    datasets = sorted(datasets_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    return datasets[0] if datasets else None


def interactive_loop(
    config_path: Path, existing_dataset: Path | None = None, verbose: bool = False
) -> None:
    """Main interactive loop for dataset verification."""
    config = load_config(config_path)

    # Use provided dataset or find latest
    if existing_dataset and existing_dataset.exists():
        dataset_dir = existing_dataset
        needs_generation = False
        print(f"Using existing dataset: {dataset_dir}")
    else:
        dataset_dir = find_latest_dataset()
        needs_generation = dataset_dir is None

    while True:
        if needs_generation:
            # Run generator
            dataset_dir = run_generator(config_path, verbose=verbose)
            if dataset_dir is None:
                print("Failed to generate dataset. Please fix errors and try again.")
                if not prompt_yes_no("Retry?"):
                    break
                continue
            needs_generation = False

        # Analyze and show stats
        stats = analyze_dataset(dataset_dir)
        print_stats(stats, config)

        # Ask for approval
        print("\nOptions:")
        print("  [a] Approve - dataset looks good")
        print("  [t] Modify task counts")
        print("  [d] Modify test distribution")
        print("  [r] Regenerate with same config")
        print("  [q] Quit without approving")

        choice = input("\nChoice [a/t/d/r/q]: ").strip().lower()

        if choice == "a":
            print(f"\nDataset approved: {dataset_dir}")
            print("Ready for upload with: ./scripts/upload.sh " + str(dataset_dir))
            break

        elif choice == "t":
            config, changed = edit_task_counts(config)
            if changed:
                save_config(config_path, config)
                print(f"\nUpdated config saved to {config_path}")
                # Delete old dataset before regenerating
                if dataset_dir.exists():
                    shutil.rmtree(dataset_dir)
                needs_generation = True
            else:
                print("\nNo changes made.")

        elif choice == "d":
            config, changed = edit_test_distribution(config)
            if changed:
                save_config(config_path, config)
                print(f"\nUpdated config saved to {config_path}")
                if dataset_dir.exists():
                    shutil.rmtree(dataset_dir)
                needs_generation = True
            else:
                print("\nNo changes made.")

        elif choice == "r":
            if dataset_dir.exists():
                shutil.rmtree(dataset_dir)
            needs_generation = True

        elif choice == "q":
            print("\nExiting without approval.")
            # Clean up generated dataset
            if dataset_dir.exists() and prompt_yes_no("Delete generated dataset?", default=False):
                shutil.rmtree(dataset_dir)
            break

        else:
            print("Invalid choice, please try again.")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive dataset verification and configuration tool"
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help="Path to dataset config YAML",
    )
    parser.add_argument(
        "--existing",
        "-e",
        type=Path,
        help="Path to existing dataset to verify (skips generation)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Stream generator output instead of showing spinner",
    )
    args = parser.parse_args()

    # Determine config path
    config_path = args.config
    if not config_path:
        config_path = Path("config/dataset.prod.yaml")
        if not config_path.exists():
            config_path = Path("config/dataset.yaml")

    if not config_path.exists():
        print(f"ERROR: Config not found: {config_path}")
        parser.print_help()
        sys.exit(1)

    if args.existing:
        # Verify existing dataset
        if not args.existing.exists():
            print(f"ERROR: Dataset not found: {args.existing}")
            sys.exit(1)
        interactive_loop(config_path, existing_dataset=args.existing, verbose=args.verbose)
    else:
        # Default: generate and verify
        interactive_loop(config_path, verbose=args.verbose)


if __name__ == "__main__":
    main()
