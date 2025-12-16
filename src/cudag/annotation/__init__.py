# Copyright (c) 2025 Tylt LLC. All rights reserved.
# CONFIDENTIAL AND PROPRIETARY. Unauthorized use, copying, or distribution
# is strictly prohibited. For licensing inquiries: hello@claimhawk.app

"""Annotation parsing and code generation for CUDAG.

This module provides utilities for parsing Annotator exports and
generating CUDAG project code from them.

Example:
    from cudag.annotation import AnnotationLoader, scaffold_generator

    loader = AnnotationLoader()
    parsed = loader.load("annotation.zip")

    scaffold_generator(
        name="my-generator",
        annotation=parsed,
        output_dir=Path("./projects"),
    )

For runtime data-driven generation:
    from cudag.annotation import AnnotationConfig

    config = AnnotationConfig.load(Path("assets/annotations"))
    for icon in config.get_labeled_icons("desktop"):
        print(f"{icon.label} at {icon.absolute_center}")

For parsing grid transcriptions:
    from cudag.annotation import parse_transcription

    grid = config.get_element_by_label("patient-account")
    if grid and grid.transcription:
        for row in grid.transcription.rows:
            print([cell.text for cell in row.cells])
"""

from cudag.annotation.config import (
    AnnotatedElement,
    AnnotatedIcon,
    AnnotatedTask,
    AnnotationConfig,
)
from cudag.annotation.loader import (
    AnnotationLoader,
    ParsedAnnotation,
    ParsedElement,
    ParsedTask,
)
from cudag.annotation.scaffold import scaffold_generator
from cudag.annotation.transcription import (
    ParsedTranscription,
    TranscriptionCell,
    TranscriptionRow,
    parse_text_transcription,
    parse_transcription,
)

__all__ = [
    # Runtime config (for data-driven generators)
    "AnnotationConfig",
    "AnnotatedElement",
    "AnnotatedIcon",
    "AnnotatedTask",
    # Transcription parsing (for grid data extraction)
    "ParsedTranscription",
    "TranscriptionCell",
    "TranscriptionRow",
    "parse_transcription",
    "parse_text_transcription",
    # Code generation (for scaffolding new generators)
    "AnnotationLoader",
    "ParsedAnnotation",
    "ParsedElement",
    "ParsedTask",
    "scaffold_generator",
]
