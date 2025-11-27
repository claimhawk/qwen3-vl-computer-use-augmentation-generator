# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Derivative works may be released by researchers,
# but original files may not be redistributed or used beyond research purposes.

"""Main CLI entrypoint for CUDAG."""

from __future__ import annotations

from pathlib import Path

import click

from cudag import __version__


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    """CUDAG - ComputerUseDataAugmentedGeneration framework.

    Create generator projects with 'cudag new', then generate datasets
    with 'cudag generate'.
    """
    pass


@cli.command()
@click.argument("name")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default=".",
    help="Directory to create the project in (default: current directory)",
)
def new(name: str, output_dir: str) -> None:
    """Create a new CUDAG project.

    NAME is the project name (e.g., 'appointment-picker').
    """
    from cudag.cli.new import create_project

    project_dir = create_project(name, Path(output_dir))
    click.echo(f"Created project: {project_dir}")
    click.echo("\nNext steps:")
    click.echo(f"  cd {project_dir}")
    click.echo("  # Edit screen.py, state.py, renderer.py, and tasks/")
    click.echo("  cudag generate --config config/dataset.yaml")


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="Path to dataset config YAML",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    help="Override output directory",
)
def generate(config: str, output_dir: str | None) -> None:
    """Generate a dataset from the current project.

    Requires a dataset config file (YAML) and the project's screen/task definitions.
    """
    config_path = Path(config)
    click.echo(f"Loading config: {config_path}")

    # TODO: Implement full generation by loading project modules
    # For now, show what would be done
    click.echo("Generation not yet implemented - use project's generate.py directly")


@cli.command()
@click.argument("dataset_dir", type=click.Path(exists=True))
def upload(dataset_dir: str) -> None:
    """Upload a dataset to Modal volume.

    DATASET_DIR is the path to the generated dataset directory.
    """
    click.echo(f"Uploading: {dataset_dir}")
    click.echo("Upload not yet implemented")


@cli.group()
def eval() -> None:
    """Evaluation commands."""
    pass


@eval.command("generate")
@click.option("--count", "-n", default=100, help="Number of eval cases")
@click.option("--dataset-dir", type=click.Path(exists=True), help="Dataset directory")
def eval_generate(count: int, dataset_dir: str | None) -> None:
    """Generate evaluation cases."""
    click.echo(f"Generating {count} eval cases")
    click.echo("Eval generation not yet implemented")


@eval.command("run")
@click.option("--checkpoint", type=click.Path(exists=True), help="Model checkpoint")
@click.option("--dataset-dir", type=click.Path(exists=True), help="Dataset directory")
def eval_run(checkpoint: str | None, dataset_dir: str | None) -> None:
    """Run evaluations on Modal."""
    click.echo("Running evaluations")
    click.echo("Eval running not yet implemented")


@cli.command()
def datasets() -> None:
    """List datasets on Modal volume."""
    click.echo("Listing datasets on Modal volume...")
    click.echo("Dataset listing not yet implemented")


if __name__ == "__main__":
    cli()
