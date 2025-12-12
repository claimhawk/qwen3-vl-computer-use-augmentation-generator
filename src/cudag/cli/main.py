# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

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


@cli.command()
@click.argument("dataset_dir", type=click.Path(exists=True))
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show all errors (default: first 10)",
)
def validate(dataset_dir: str, verbose: bool) -> None:
    """Validate a dataset against the CUDAG schema.

    DATASET_DIR is the path to the generated dataset directory.

    Checks:
    - Required filesystem structure (images/, test/, etc.)
    - Training record schema (data.jsonl, train.jsonl, val.jsonl)
    - Test record schema (test/test.json)
    - Image path validity (all referenced images exist)

    Exit codes:
    - 0: Dataset is valid
    - 1: Validation errors found
    """
    from cudag.validation import validate_dataset

    dataset_path = Path(dataset_dir)
    errors = validate_dataset(dataset_path)

    if not errors:
        click.secho(f"Dataset valid: {dataset_dir}", fg="green")
        raise SystemExit(0)

    # Show errors
    click.secho(f"Found {len(errors)} validation error(s):", fg="red")
    display_errors = errors if verbose else errors[:10]
    for error in display_errors:
        click.echo(f"  {error}")

    if not verbose and len(errors) > 10:
        click.echo(f"  ... and {len(errors) - 10} more (use -v to see all)")

    raise SystemExit(1)


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


@cli.command()
@click.option(
    "--host",
    "-h",
    default="127.0.0.1",
    help="Host to bind to (default: 127.0.0.1)",
)
@click.option(
    "--port",
    "-p",
    default=8420,
    help="Port to listen on (default: 8420)",
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload for development",
)
def serve(host: str, port: int, reload: bool) -> None:
    """Start the CUDAG server for annotation integration.

    The server provides a REST API that the Annotator UI can use
    to generate CUDAG projects without using the terminal.

    Endpoints:
      GET  /health           - Health check
      POST /api/v1/generate  - Generate project from annotation
      GET  /api/v1/status/{job_id} - Check generation progress
    """
    from cudag.server import run_server

    click.echo(f"Starting CUDAG server on http://{host}:{port}")
    click.echo("Press Ctrl+C to stop")
    run_server(host=host, port=port, reload=reload)


@cli.command("from-annotation")
@click.argument("annotation_path", type=click.Path(exists=True))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default=".",
    help="Directory to create the project in (default: current directory)",
)
@click.option(
    "--name",
    "-n",
    help="Project name (default: derived from annotation)",
)
@click.option(
    "--in-place",
    "-i",
    is_flag=True,
    help="Write directly to output-dir without creating a subdirectory",
)
def from_annotation(
    annotation_path: str, output_dir: str, name: str | None, in_place: bool
) -> None:
    """Create a CUDAG project from an annotation folder or ZIP.

    ANNOTATION_PATH is the path to an annotation folder or .zip file
    exported from the Annotator application. The folder should contain:
    - annotation.json: Element and task definitions
    - original.png: Original screenshot
    - masked.png: Screenshot with masked regions
    - icons/: Optional folder with extracted icons

    This generates a complete project structure with:
    - screen.py: Screen definition with regions
    - state.py: State class for dynamic content
    - renderer.py: Renderer using the masked image
    - tasks/: Task files for each defined task
    - config/: Dataset configuration
    - assets/: Base images and icons
    """
    import zipfile
    from cudag.annotation import AnnotationLoader, scaffold_generator

    loader = AnnotationLoader()
    annotation_source = Path(annotation_path)

    try:
        parsed = loader.load(annotation_source)
    except Exception as e:
        click.secho(f"Error loading annotation: {e}", fg="red")
        raise SystemExit(1)

    project_name = name or parsed.screen_name

    # Load images from folder or ZIP
    if annotation_source.is_dir():
        # Load from folder
        original_path = annotation_source / "original.png"
        masked_path = annotation_source / "masked.png"
        icons_dir = annotation_source / "icons"

        original_bytes = original_path.read_bytes() if original_path.exists() else None
        masked_bytes = masked_path.read_bytes() if masked_path.exists() else None

        icons: dict[str, bytes] = {}
        if icons_dir.exists():
            for icon_file in icons_dir.glob("*.png"):
                icons[icon_file.stem] = icon_file.read_bytes()
    else:
        # Load from ZIP
        if not annotation_source.suffix == ".zip":
            click.secho("Error: Expected a folder or .zip file", fg="red")
            raise SystemExit(1)

        with zipfile.ZipFile(annotation_source) as zf:
            original_bytes = (
                zf.read("original.png") if "original.png" in zf.namelist() else None
            )
            masked_bytes = (
                zf.read("masked.png") if "masked.png" in zf.namelist() else None
            )

            icons = {}
            for filename in zf.namelist():
                if filename.startswith("icons/") and filename.endswith(".png"):
                    icon_name = Path(filename).stem
                    icons[icon_name] = zf.read(filename)

    # Scaffold project
    output_path = Path(output_dir)
    files = scaffold_generator(
        name=project_name,
        annotation=parsed,
        output_dir=output_path,
        original_image=original_bytes,
        masked_image=masked_bytes,
        icons=icons,
        in_place=in_place,
    )

    project_dir = output_path if in_place else output_path / project_name
    click.secho(f"Created project: {project_dir}", fg="green")
    click.echo(f"\nGenerated {len(files)} files:")
    for f in files[:10]:
        click.echo(f"  {f.relative_to(project_dir)}")
    if len(files) > 10:
        click.echo(f"  ... and {len(files) - 10} more")

    click.echo("\nNext steps:")
    click.echo(f"  cd {project_dir}")
    click.echo("  # Review and customize generated code")
    click.echo("  python generator.py --samples 100")


if __name__ == "__main__":
    cli()
