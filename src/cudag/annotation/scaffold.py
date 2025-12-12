# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Generator scaffolding from parsed annotations."""

from __future__ import annotations

import json
from pathlib import Path

from cudag.annotation.loader import ParsedAnnotation
from cudag.annotation.codegen import (
    generate_screen_py,
    generate_state_py,
    generate_renderer_py,
    generate_generator_py,
    generate_task_py,
    generate_tasks_init_py,
    generate_config_yaml,
    generate_pyproject_toml,
)


def scaffold_generator(
    name: str,
    annotation: ParsedAnnotation,
    output_dir: Path,
    original_image: bytes | None = None,
    masked_image: bytes | None = None,
    icons: dict[str, bytes] | None = None,
    in_place: bool = False,
) -> list[Path]:
    """Scaffold a complete CUDAG generator project from annotation.

    Uses annotation-driven architecture where annotation.json is loaded at
    runtime via AnnotationConfig, enabling updates without regenerating code.

    Args:
        name: Project name (used for directory name)
        annotation: Parsed annotation data
        output_dir: Parent directory for the project
        original_image: Original screenshot bytes
        masked_image: Masked image bytes (with dynamic regions blanked)
        icons: Map of icon names to image bytes (optional)
        in_place: If True, write directly to output_dir without creating subdirectory

    Returns:
        List of created file paths
    """
    project_dir = output_dir if in_place else output_dir / name
    project_dir.mkdir(parents=True, exist_ok=True)

    created_files: list[Path] = []

    # Create directory structure (annotation-driven layout)
    (project_dir / "tasks").mkdir(exist_ok=True)
    (project_dir / "assets" / "annotations").mkdir(parents=True, exist_ok=True)
    (project_dir / "assets" / "icons").mkdir(exist_ok=True)
    (project_dir / "config").mkdir(exist_ok=True)

    # Save annotation.json (single source of truth)
    annotation_json = project_dir / "assets" / "annotations" / "annotation.json"
    annotation_json.write_text(json.dumps(annotation.to_dict(), indent=2))
    created_files.append(annotation_json)

    # Generate Python files
    screen_py = project_dir / "screen.py"
    screen_py.write_text(generate_screen_py(annotation))
    created_files.append(screen_py)

    state_py = project_dir / "state.py"
    state_py.write_text(generate_state_py(annotation))
    created_files.append(state_py)

    renderer_py = project_dir / "renderer.py"
    renderer_py.write_text(generate_renderer_py(annotation))
    created_files.append(renderer_py)

    generator_py = project_dir / "generator.py"
    generator_py.write_text(generate_generator_py(annotation))
    created_files.append(generator_py)

    # Generate task files
    tasks_init = project_dir / "tasks" / "__init__.py"
    tasks_init.write_text(generate_tasks_init_py(annotation.tasks))
    created_files.append(tasks_init)

    for task in annotation.tasks:
        task_file = project_dir / "tasks" / f"{task.python_name}.py"
        task_file.write_text(generate_task_py(task, annotation))
        created_files.append(task_file)

    # Generate config
    config_yaml = project_dir / "config" / "dataset.yaml"
    config_yaml.write_text(generate_config_yaml(annotation))
    created_files.append(config_yaml)

    # Generate pyproject.toml
    pyproject = project_dir / "pyproject.toml"
    pyproject.write_text(generate_pyproject_toml(name))
    created_files.append(pyproject)

    # Save images to annotations directory
    if original_image:
        original_png = project_dir / "assets" / "annotations" / "original.png"
        original_png.write_bytes(original_image)
        created_files.append(original_png)

    if masked_image:
        masked_png = project_dir / "assets" / "annotations" / "masked.png"
        masked_png.write_bytes(masked_image)
        created_files.append(masked_png)

    if icons:
        for icon_name, icon_bytes in icons.items():
            icon_path = project_dir / "assets" / "icons" / f"{icon_name}.png"
            icon_path.write_bytes(icon_bytes)
            created_files.append(icon_path)

    return created_files
