# Copyright (c) 2025 Tylt LLC. All rights reserved.
"""Tests for CLI commands."""

import tempfile
from pathlib import Path

import pytest

from cudag.cli.new import create_project


class TestCreateProject:
    """Tests for create_project function."""

    def test_creates_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project("test-project", Path(tmpdir))
            assert project_dir.exists()
            assert project_dir.is_dir()
            assert project_dir.name == "test-project"

    def test_creates_standard_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project("my-generator", Path(tmpdir))

            # Check directories
            assert (project_dir / "config").is_dir()
            assert (project_dir / "tasks").is_dir()
            assert (project_dir / "assets").is_dir()
            assert (project_dir / "datasets").is_dir()
            assert (project_dir / "models").is_dir()

    def test_creates_core_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project("my-generator", Path(tmpdir))

            # Check files exist
            assert (project_dir / "pyproject.toml").is_file()
            assert (project_dir / ".gitignore").is_file()
            assert (project_dir / "screen.py").is_file()
            assert (project_dir / "state.py").is_file()
            assert (project_dir / "renderer.py").is_file()
            assert (project_dir / "README.md").is_file()

    def test_creates_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project("test-gen", Path(tmpdir))
            config_file = project_dir / "config" / "dataset.yaml"
            assert config_file.is_file()
            content = config_file.read_text()
            assert "test-gen" in content
            assert "tasks:" in content

    def test_creates_models_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project("test-gen", Path(tmpdir))
            models_init = project_dir / "models" / "__init__.py"
            assert models_init.is_file()
            content = models_init.read_text()
            assert "Model" in content
            assert "Patient" in content

    def test_creates_tasks_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project("test-gen", Path(tmpdir))
            tasks_init = project_dir / "tasks" / "__init__.py"
            assert tasks_init.is_file()

    def test_creates_example_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project("test-gen", Path(tmpdir))
            example_task = project_dir / "tasks" / "example_task.py"
            assert example_task.is_file()
            content = example_task.read_text()
            assert "BaseTask" in content
            assert "TaskSample" in content
            assert "generate_sample" in content

    def test_normalizes_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Spaces and underscores should become dashes
            project_dir = create_project("My Test_Project", Path(tmpdir))
            assert project_dir.name == "my-test-project"

    def test_pyproject_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project("test-gen", Path(tmpdir))
            pyproject = project_dir / "pyproject.toml"
            content = pyproject.read_text()
            assert 'name = "test-gen"' in content
            assert "cudag" in content
            assert "pillow" in content.lower()

    def test_gitignore_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project("test-gen", Path(tmpdir))
            gitignore = project_dir / ".gitignore"
            content = gitignore.read_text()
            assert "__pycache__" in content
            assert "datasets/" in content
            assert ".venv/" in content

    def test_screen_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project("claim-window", Path(tmpdir))
            screen_file = project_dir / "screen.py"
            content = screen_file.read_text()
            # Should have class name derived from project name
            assert "ClaimWindowScreen" in content
            assert "Screen" in content

    def test_state_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project("claim-window", Path(tmpdir))
            state_file = project_dir / "state.py"
            content = state_file.read_text()
            assert "ClaimWindowState" in content
            assert "BaseState" in content

    def test_renderer_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project("claim-window", Path(tmpdir))
            renderer_file = project_dir / "renderer.py"
            content = renderer_file.read_text()
            assert "ClaimWindowRenderer" in content
            assert "BaseRenderer" in content
            assert "load_assets" in content
            assert "render" in content

    def test_readme_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = create_project("my-project", Path(tmpdir))
            readme = project_dir / "README.md"
            content = readme.read_text()
            assert "# my-project" in content
            assert "cudag generate" in content

    def test_idempotent(self) -> None:
        """Creating same project twice should not fail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir1 = create_project("test-gen", Path(tmpdir))
            project_dir2 = create_project("test-gen", Path(tmpdir))
            assert project_dir1 == project_dir2
