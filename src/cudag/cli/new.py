# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Derivative works may be released by researchers,
# but original files may not be redistributed or used beyond research purposes.

"""Project scaffolding for cudag new command."""

from __future__ import annotations

import shutil
import stat
from pathlib import Path
from textwrap import dedent


def create_project(name: str, parent_dir: Path) -> Path:
    """Create a new CUDAG project with scaffolding.

    Args:
        name: Project name (e.g., "appointment-picker")
        parent_dir: Directory to create project in

    Returns:
        Path to created project directory
    """
    # Normalize name
    project_name = name.lower().replace(" ", "-").replace("_", "-")
    module_name = project_name.replace("-", "_")

    project_dir = parent_dir / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create directory structure
    (project_dir / "config").mkdir(exist_ok=True)
    (project_dir / "tasks").mkdir(exist_ok=True)
    (project_dir / "assets").mkdir(exist_ok=True)
    (project_dir / "datasets").mkdir(exist_ok=True)
    (project_dir / "models").mkdir(exist_ok=True)
    (project_dir / "scripts").mkdir(exist_ok=True)
    (project_dir / "modal_apps").mkdir(exist_ok=True)

    # Create files
    _write_pyproject(project_dir, project_name, module_name)
    _write_gitignore(project_dir)
    _write_screen(project_dir, module_name)
    _write_state(project_dir, module_name)
    _write_renderer(project_dir, module_name)
    _write_generator(project_dir, module_name)
    _write_models_init(project_dir, module_name)
    _write_tasks_init(project_dir)
    _write_example_task(project_dir, module_name)
    _write_dataset_config(project_dir, project_name)
    _write_readme(project_dir, project_name)
    _write_scripts(project_dir, module_name)
    _write_modal_apps(project_dir)
    _write_makefile(project_dir, module_name)
    _write_copyright(project_dir)
    _init_git(project_dir)

    return project_dir


def _write_pyproject(project_dir: Path, project_name: str, module_name: str) -> None:
    """Write pyproject.toml."""
    content = dedent(f'''\
        [build-system]
        requires = ["hatchling"]
        build-backend = "hatchling.build"

        [project]
        name = "{project_name}"
        version = "0.1.0"
        description = "CUDAG project for {project_name}"
        requires-python = ">=3.11"
        dependencies = [
            "cudag",
            "pillow>=10.0.0",
            "pyyaml>=6.0",
        ]

        [tool.uv.sources]
        cudag = {{ path = "../../cudag", editable = true }}

        [project.optional-dependencies]
        dev = [
            "ruff>=0.1.0",
            "mypy>=1.0.0",
            "types-PyYAML>=6.0.0",
        ]

        [tool.hatch.build.targets.wheel]
        packages = ["."]

        [tool.ruff]
        line-length = 100
        target-version = "py311"

        [tool.mypy]
        python_version = "3.11"
        strict = true
    ''')
    (project_dir / "pyproject.toml").write_text(content)


def _write_gitignore(project_dir: Path) -> None:
    """Write .gitignore."""
    content = dedent("""\
        # Python
        __pycache__/
        *.py[cod]
        .venv/
        *.egg-info/

        # Generated datasets
        datasets/

        # IDE
        .idea/
        .vscode/
        *.swp
    """)
    (project_dir / ".gitignore").write_text(content)


def _write_screen(project_dir: Path, module_name: str) -> None:
    """Write screen.py with example Screen class."""
    class_name = "".join(word.title() for word in module_name.split("_")) + "Screen"
    renderer_name = class_name.replace("Screen", "Renderer")

    content = dedent(f'''\
        # Copyright (c) 2025 Tylt LLC. All rights reserved.
        # Derivative works may be released by researchers,
        # but original files may not be redistributed or used beyond research purposes.

        """Screen definition for {module_name}."""

        from typing import Any, NoReturn

        from cudag.core import Screen

        # Uncomment to use these region types:
        # from cudag.core import Bounds, ButtonRegion, GridRegion, ClickRegion


        class {class_name}(Screen):
            """Define the screen layout and interactive regions.

            Edit this class to define your screen's regions:
            - ButtonRegion for clickable buttons
            - GridRegion for grid-like clickable areas
            - ScrollRegion for scrollable areas
            - DropdownRegion for dropdown menus
            """

            class Meta:
                name = "{module_name}"
                base_image = "assets/base.png"  # Your base screenshot
                size = (800, 600)  # Image dimensions

            # Example: Define a clickable grid region
            # grid = GridRegion(
            #     bounds=Bounds(x=100, y=100, width=400, height=300),
            #     rows=5,
            #     cols=4,
            # )

            # Example: Define a button
            # submit_button = ButtonRegion(
            #     bounds=Bounds(x=350, y=450, width=100, height=40),
            #     label="Submit",
            #     description="Submit the form",
            # )

            def render(self, state: Any) -> NoReturn:
                """Render is handled by the Renderer class."""
                raise NotImplementedError("Use {renderer_name} instead")
    ''')
    (project_dir / "screen.py").write_text(content)


def _write_state(project_dir: Path, module_name: str) -> None:
    """Write state.py with example State class."""
    class_name = "".join(word.title() for word in module_name.split("_")) + "State"

    content = dedent(f'''\
        # Copyright (c) 2025 Tylt LLC. All rights reserved.
        # Derivative works may be released by researchers,
        # but original files may not be redistributed or used beyond research purposes.

        """State definition for {module_name}."""

        from dataclasses import dataclass
        from cudag.core import BaseState


        @dataclass
        class {class_name}(BaseState):
            """Dynamic data that populates the screen.

            Add fields for all the data needed to render your screen.
            """

            # Example fields - replace with your own:
            # selected_item: int = 0
            # items: list[str] = field(default_factory=list)

            pass  # Remove this when you add fields
    ''')
    (project_dir / "state.py").write_text(content)


def _write_renderer(project_dir: Path, module_name: str) -> None:
    """Write renderer.py with example Renderer class."""
    screen_class = "".join(word.title() for word in module_name.split("_")) + "Screen"
    state_class = "".join(word.title() for word in module_name.split("_")) + "State"
    renderer_class = "".join(word.title() for word in module_name.split("_")) + "Renderer"

    content = dedent(f'''\
        # Copyright (c) 2025 Tylt LLC. All rights reserved.
        # Derivative works may be released by researchers,
        # but original files may not be redistributed or used beyond research purposes.

        """Renderer for {module_name}."""

        from typing import Any

        from PIL import Image

        from cudag.core import BaseRenderer

        from screen import {screen_class}
        from state import {state_class}


        class {renderer_class}(BaseRenderer[{state_class}]):
            """Renders the {module_name} screen.

            Loads assets and generates images from state.
            """

            screen_class = {screen_class}

            def load_assets(self) -> None:
                """Load fonts and other assets."""
                # Example:
                # from PIL import ImageFont
                # self.font = ImageFont.truetype(self.asset_path("fonts", "arial.ttf"), 12)
                pass

            def render(self, state: {state_class}) -> tuple[Image.Image, dict[str, Any]]:
                """Render the screen with given state.

                Args:
                    state: Current screen state

                Returns:
                    (PIL Image, metadata dict)
                """
                # Load base image
                image = self.load_base_image()

                # TODO: Draw state onto image
                # Example:
                # draw = ImageDraw.Draw(image)
                # draw.text((100, 100), state.some_field, fill="black")

                # Build metadata
                metadata = self.build_metadata(state)

                return image, metadata
    ''')
    (project_dir / "renderer.py").write_text(content)


def _write_generator(project_dir: Path, module_name: str) -> None:
    """Write generator.py - main entry point for dataset generation."""
    renderer_class = "".join(word.title() for word in module_name.split("_")) + "Renderer"

    content = dedent(f'''\
        # Copyright (c) 2025 Tylt LLC. All rights reserved.
        # Derivative works may be released by researchers,
        # but original files may not be redistributed or used beyond research purposes.

        """Dataset generator for {module_name}.

        Usage:
            python generator.py
            python generator.py --config config/dataset.yaml
        """

        import argparse
        from datetime import datetime
        from pathlib import Path

        from cudag.core import DatasetBuilder, DatasetConfig

        from renderer import {renderer_class}
        from tasks.example_task import ExampleTask


        def get_researcher_name() -> str | None:
            """Get researcher name from .researcher file if it exists."""
            researcher_file = Path(".researcher")
            if researcher_file.exists():
                content = researcher_file.read_text().strip()
                for line in content.split("\\n"):
                    if line.startswith("Name:"):
                        return line.split(":", 1)[1].strip().lower()
            return None


        def main() -> None:
            """Run dataset generation."""
            parser = argparse.ArgumentParser(description="Generate dataset")
            parser.add_argument(
                "--config",
                type=Path,
                default=Path("config/dataset.yaml"),
                help="Path to dataset config YAML",
            )
            args = parser.parse_args()

            # Load config
            config = DatasetConfig.from_yaml(args.config)

            # Build dataset name with timestamp
            researcher = get_researcher_name()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if researcher:
                dataset_name = f"{{config.name_prefix}}--{{researcher}}--{{timestamp}}"
            else:
                dataset_name = f"{{config.name_prefix}}_{{timestamp}}"

            # Override output_dir with new naming
            config.output_dir = Path("datasets") / dataset_name

            print(f"Loaded config: {{config.name_prefix}}")
            print(f"Tasks: {{config.task_counts}}")

            # Initialize renderer
            renderer = {renderer_class}(assets_dir=Path("assets"))
            renderer.load_assets()

            # Create tasks - add your tasks here
            tasks = [
                ExampleTask(config=config, renderer=renderer),
                # Add more tasks as needed
            ]

            # Build dataset
            builder = DatasetBuilder(config=config, tasks=tasks)
            output_dir = builder.build()

            # Build tests
            builder.build_tests()

            print(f"\\nDataset generated at: {{output_dir}}")


        if __name__ == "__main__":
            main()
    ''')
    (project_dir / "generator.py").write_text(content)


def _write_models_init(project_dir: Path, module_name: str) -> None:
    """Write models/__init__.py with example Model classes."""
    content = dedent(f'''\
        # Copyright (c) 2025 Tylt LLC. All rights reserved.
        # Derivative works may be released by researchers,
        # but original files may not be redistributed or used beyond research purposes.

        """Domain models for {module_name}.

        Define your data types here (Patient, Provider, Claim, etc.)
        with field definitions for realistic data generation.
        """

        # Re-export common models for use in this project
        from cudag.core import Claim as Claim
        from cudag.core import Patient as Patient
        from cudag.core import Procedure as Procedure
        from cudag.core import Provider as Provider

        # Import types for custom model definitions:
        # from cudag.core import (
        #     Model,
        #     StringField,
        #     IntField,
        #     DateField,
        #     ChoiceField,
        #     MoneyField,
        # )

        # Example: Define a custom model
        # class MyCustomModel(Model):
        #     name = StringField(faker="full_name")
        #     account_number = StringField(pattern=r"[A-Z]{{2}}[0-9]{{8}}")
        #     status = ChoiceField(choices=["Active", "Pending", "Closed"])

        __all__ = [
            "Patient",
            "Provider",
            "Procedure",
            "Claim",
        ]
    ''')
    (project_dir / "models" / "__init__.py").write_text(content)


def _write_tasks_init(project_dir: Path) -> None:
    """Write tasks/__init__.py."""
    content = dedent('''\
        # Copyright (c) 2025 Tylt LLC. All rights reserved.
        # Derivative works may be released by researchers,
        # but original files may not be redistributed or used beyond research purposes.

        """Task definitions for this project."""

        # Import your tasks here:
        # from tasks.click_item import ClickItemTask
    ''')
    (project_dir / "tasks" / "__init__.py").write_text(content)


def _write_example_task(project_dir: Path, module_name: str) -> None:
    """Write an example task file."""
    state_class = "".join(word.title() for word in module_name.split("_")) + "State"

    content = dedent(f'''\
        # Copyright (c) 2025 Tylt LLC. All rights reserved.
        # Derivative works may be released by researchers,
        # but original files may not be redistributed or used beyond research purposes.

        """Example task - demonstrates 1-image-to-many-samples pattern with distributions.

        Key insight: One rendered image can produce MULTIPLE training samples.
        This is more efficient than generating a new image for each sample.

        IMPORTANT: All coordinates in training data MUST be normalized RU (0-1000).
        Use normalize_coord() before passing to ToolCall.

        Distribution Pattern:
        - Configure distributions in dataset.yaml under task_distributions
        - Use ctx.config or DatasetConfig.sample_distribution_type() to select type
        - Generate samples according to the distribution (normal, edge_case, adversarial)
        """

        from cudag.core import BaseTask, DatasetConfig, TaskContext, TaskSample, TestCase
        from cudag.core.coords import normalize_coord
        from cudag.prompts.tools import ToolCall

        from state import {state_class}


        class ExampleTask(BaseTask):
            """Example task demonstrating 1:N image-to-samples pattern with distributions.

            One Screen can have many Tasks. Each Task:
            - Belongs to a Screen
            - Has a task_type identifier
            - Can generate multiple samples from one rendered image
            - Supports distribution-based sample generation

            Example use cases:
            - Same claim window -> "click code" + "click fee" + "scroll"
            - Same calendar -> "click day 1" + "click day 15"

            Distribution Example (in dataset.yaml):
                task_distributions:
                  example-click:
                    normal: 0.80       # 80% normal cases
                    edge_case: 0.15   # 15% edge cases
                    adversarial: 0.05 # 5% no valid target
            """

            task_type = "example-click"

            def __init__(self, config: dict | DatasetConfig, renderer: "BaseRenderer") -> None:
                super().__init__(config, renderer)
                # Store DatasetConfig for distribution sampling
                self._dataset_config: DatasetConfig | None = None
                if isinstance(config, DatasetConfig):
                    self._dataset_config = config

            def _get_distribution_type(self, ctx: TaskContext) -> str:
                """Sample distribution type from config, with defaults."""
                if self._dataset_config:
                    dist_type = self._dataset_config.sample_distribution_type(
                        self.task_type, ctx.rng
                    )
                    if dist_type:
                        return dist_type
                # Default distribution if not configured
                roll = ctx.rng.random()
                if roll < 0.80:
                    return "normal"
                elif roll < 0.95:
                    return "edge_case"
                else:
                    return "adversarial"

            def generate_samples(self, ctx: TaskContext) -> list[TaskSample]:
                """Generate MULTIPLE samples from ONE rendered image."""
                # 1. Determine distribution type for this sample
                dist_type = self._get_distribution_type(ctx)

                # 2. Create state and render ONCE
                state = {state_class}()
                image, metadata = self.renderer.render(state)
                image_path = self.save_image(image, ctx)

                samples = []

                # 3. Generate samples based on distribution type
                if dist_type == "adversarial":
                    # Adversarial: No valid target - model should respond with "answer"
                    samples.append(TaskSample(
                        id=self.build_id(ctx, "_adversarial"),
                        image_path=image_path,
                        human_prompt="Click the nonexistent item",
                        tool_call=ToolCall(
                            action="answer",
                            text="There is no such item on the screen."
                        ),
                        pixel_coords=(0, 0),
                        metadata={{
                            "task_type": self.task_type,
                            "distribution": dist_type,
                            "has_match": False,
                        }},
                        image_size=image.size,
                    ))
                else:
                    # Normal or edge_case: valid targets exist
                    # IMPORTANT: Always normalize pixel coords before ToolCall!
                    pixel_coords_1 = (400, 300)
                    norm_coords_1 = normalize_coord(pixel_coords_1, image.size)
                    samples.append(TaskSample(
                        id=self.build_id(ctx, "_target1"),
                        image_path=image_path,
                        human_prompt="Click the first item",
                        tool_call=ToolCall.left_click(norm_coords_1),  # NORMALIZED!
                        pixel_coords=pixel_coords_1,
                        metadata={{
                            "task_type": self.task_type,
                            "distribution": dist_type,
                            "has_match": True,
                            "target": "first",
                        }},
                        image_size=image.size,
                    ))

                    # For normal distribution, add more samples from same image
                    if dist_type == "normal":
                        pixel_coords_2 = (500, 400)
                        norm_coords_2 = normalize_coord(pixel_coords_2, image.size)
                        samples.append(TaskSample(
                            id=self.build_id(ctx, "_target2"),
                            image_path=image_path,
                            human_prompt="Click the second item",
                            tool_call=ToolCall.left_click(norm_coords_2),  # NORMALIZED!
                            pixel_coords=pixel_coords_2,
                            metadata={{
                                "task_type": self.task_type,
                                "distribution": dist_type,
                                "has_match": True,
                                "target": "second",
                            }},
                            image_size=image.size,
                        ))

                return samples

            def generate_sample(self, ctx: TaskContext) -> TaskSample:
                """Generate one training sample (fallback)."""
                return self.generate_samples(ctx)[0]

            def generate_tests(self, ctx: TaskContext) -> list[TestCase]:
                """Generate test cases from ONE rendered image."""
                samples = self.generate_samples(ctx)
                return [
                    TestCase(
                        test_id=f"test_{{ctx.index:04d}}_{{i}}",
                        screenshot=s.image_path,
                        prompt=s.human_prompt,
                        expected_action=s.tool_call.to_dict(),
                        tolerance=10,
                        metadata=s.metadata,
                        pixel_coords=s.pixel_coords,
                    )
                    for i, s in enumerate(samples)
                ]

            def generate_test(self, ctx: TaskContext) -> TestCase:
                """Generate one test case (fallback)."""
                return self.generate_tests(ctx)[0]
    ''')
    (project_dir / "tasks" / "example_task.py").write_text(content)


def _write_dataset_config(project_dir: Path, project_name: str) -> None:
    """Write config/dataset.yaml."""
    content = dedent(f"""\
        # Dataset configuration for {project_name}

        name_prefix: {project_name}
        seed: 42

        # Task counts - how many samples of each type
        tasks:
          example-click: 100

        # Task distributions - distribution of sample types within each task
        # Each task can have its own distribution of subtypes.
        # The values should sum to 1.0 (100%).
        # task_distributions:
        #   example-click:
        #     normal: 0.80       # 80% normal cases
        #     edge_case: 0.15   # 15% edge cases
        #     adversarial: 0.05 # 5% adversarial (no match)

        # Train/test split
        splits:
          train: 0.8

        # System prompt style
        system_prompt: computer-use

        # Output settings
        output:
          image_format: png
          image_quality: 95

        # Test settings (held-out evaluation data)
        test:
          count: 20
          tolerance: 10

        # Annotation settings
        annotation:
          enabled: true
          per_type:
            example-click: 2
    """)
    (project_dir / "config" / "dataset.yaml").write_text(content)


def _write_readme(project_dir: Path, project_name: str) -> None:
    """Write README.md."""
    content = dedent(f"""\
        # {project_name}

        CUDAG project for generating training data.

        ## Setup

        ```bash
        pip install -e .
        ```

        ## Structure

        - `screen.py` - Screen definition (regions, layout)
        - `state.py` - State dataclass (dynamic data)
        - `renderer.py` - Image rendering logic
        - `models/` - Domain model definitions (Patient, Provider, etc.)
        - `tasks/` - Task implementations
        - `config/` - Dataset configurations
        - `assets/` - Base images, fonts, etc.

        ## Usage

        ```bash
        # Generate dataset
        cudag generate --config config/dataset.yaml

        # Or run directly
        python generate.py --config config/dataset.yaml
        ```

        ## Development

        1. Edit `screen.py` to define your UI regions
        2. Edit `state.py` to define your data model
        3. Edit `renderer.py` to implement image generation
        4. Add domain models in `models/` for data generation
        5. Add tasks in `tasks/` for each interaction type
        6. Configure dataset.yaml with sample counts
    """)
    (project_dir / "README.md").write_text(content)


def _get_templates_dir() -> Path:
    """Get the path to the templates directory."""
    return Path(__file__).parent.parent / "templates"


def _write_scripts(project_dir: Path, module_name: str) -> None:
    """Copy shell scripts from templates to the project."""
    templates_dir = _get_templates_dir()
    scripts_template_dir = templates_dir / "scripts"

    # Copy all script files from templates
    for script_file in scripts_template_dir.glob("*.sh"):
        dest_path = project_dir / "scripts" / script_file.name
        shutil.copy(script_file, dest_path)
        # Make executable
        dest_path.chmod(dest_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _write_modal_apps(project_dir: Path) -> None:
    """Copy modal_apps from templates to the project."""
    templates_dir = _get_templates_dir()
    modal_apps_template_dir = templates_dir / "modal_apps"

    # Copy all Python files from templates
    for py_file in modal_apps_template_dir.glob("*.py"):
        dest_path = project_dir / "modal_apps" / py_file.name
        shutil.copy(py_file, dest_path)


def _write_makefile(project_dir: Path, module_name: str) -> None:
    """Write Makefile for code quality and build tasks."""
    content = dedent(f'''\
        # Copyright (c) 2025 Tylt LLC. All rights reserved.
        # Derivative works may be released by researchers,
        # but original files may not be redistributed or used beyond research purposes.

        .PHONY: all check lint typecheck format clean install dev test build generate

        # Use venv Python if available, fallback to python3
        PYTHON := $(shell test -x .venv/bin/python && echo .venv/bin/python || echo python3)
        SRC_FILES := $(shell find . -name "*.py" -not -path "./.venv/*")

        # Default target
        all: check

        # Setup virtualenv and install dependencies
        install:
        \tpython3 -m venv .venv
        \t.venv/bin/pip install -e .

        # Install dev dependencies
        dev: install
        \t.venv/bin/pip install -e ".[dev]"
        \t.venv/bin/pip install radon

        # Run all quality checks
        check: lint typecheck
        \t@echo "✓ All checks passed!"

        # Linting with ruff
        lint:
        \t@echo "Running ruff..."
        \t$(PYTHON) -m ruff check $(SRC_FILES)
        \t$(PYTHON) -m ruff format --check $(SRC_FILES)

        # Type checking with mypy
        typecheck:
        \t@echo "Running mypy..."
        \t$(PYTHON) -m mypy $(SRC_FILES) --strict

        # Auto-format code
        format:
        \t@echo "Formatting code..."
        \t$(PYTHON) -m ruff format $(SRC_FILES)
        \t$(PYTHON) -m ruff check --fix $(SRC_FILES)

        # Clean build artifacts
        clean:
        \trm -rf build/ dist/ *.egg-info/
        \tfind . -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true
        \tfind . -type f -name "*.pyc" -delete 2>/dev/null || true

        # Generate dataset
        generate:
        \t./scripts/generate.sh --dry

        # Build and upload
        build:
        \t./scripts/build.sh
    ''')
    (project_dir / "Makefile").write_text(content)


def _write_copyright(project_dir: Path) -> None:
    """Write COPYRIGHT.txt file."""
    content = dedent('''\
        Copyright (c) 2025 Tylt LLC. All rights reserved.

        Derivative works may be released by researchers,
        but original files may not be redistributed or used beyond research purposes.
    ''')
    (project_dir / "COPYRIGHT.txt").write_text(content)


def _init_git(project_dir: Path) -> None:
    """Initialize git repository with pre-commit hook."""
    import subprocess

    # Initialize git
    subprocess.run(["git", "init"], cwd=project_dir, capture_output=True)

    # Create .git/hooks directory if needed
    hooks_dir = project_dir / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Write pre-commit hook
    precommit_hook = dedent('''\
        #!/usr/bin/env bash
        # Pre-commit hook - runs code quality checks on staged files

        exec ./scripts/pre-commit.sh
    ''')
    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text(precommit_hook)
    hook_path.chmod(hook_path.stat().st_mode | 0o755)

    # Write .gitattributes
    gitattributes = dedent('''\
        # Auto detect text files and perform LF normalization
        * text=auto

        # Python files
        *.py text diff=python

        # Shell scripts
        *.sh text eol=lf

        # Binary files
        *.png binary
        *.jpg binary
        *.jpeg binary
        *.gif binary
        *.ico binary
        *.ttf binary
        *.woff binary
        *.woff2 binary
    ''')
    (project_dir / ".gitattributes").write_text(gitattributes)

    # Stage all files
    subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)

    # Make initial commit (skip hooks since cudag isn't installed yet)
    result = subprocess.run(
        [
            "git",
            "commit",
            "--no-verify",  # Skip pre-commit hook (cudag not installed yet)
            "-m",
            "Initial project scaffolding from cudag new",
        ],
        cwd=project_dir,
        capture_output=True,
    )

    # If commit failed due to missing author, try with explicit author
    if result.returncode != 0:
        subprocess.run(
            [
                "git",
                "-c", "user.email=cudag@example.com",
                "-c", "user.name=CUDAG",
                "commit",
                "--no-verify",
                "-m",
                "Initial project scaffolding from cudag new",
            ],
            cwd=project_dir,
            capture_output=True,
        )
