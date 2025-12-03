# Repository Guidelines

This file provides guidance to AI coding assistants when working with code in this repository.

## Project Overview

This is CUDAG (Computer Use Dataset Action Generator) - the framework for creating screen generators that produce synthetic screenshots and action labels for training vision-language models.

## Code Quality

- Target Python 3.12+, four-space indentation, and PEP 8 defaults
- All Python code must pass ruff, mypy, and radon checks
- Maximum cyclomatic complexity: 10
- All functions must have type hints

## Commands

```bash
pip install -e .
cudag new my-generator  # Create new generator
```

## Coordinate System

All coordinates use RU (Resolution Units) normalized to [0, 1000]:
- Conversion: `normalized = (pixel / image_dimension) * 1000`

## Git Commits

**DO NOT CO-AUTHOR COMMITS** - only use the GitHub user's name when committing. Do not add co-author trailers or attribute commits to AI assistants.
