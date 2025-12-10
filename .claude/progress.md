# CUDAG Development Timeline

## Overview

CUDAG (Computer Use Dataset Augmented Generation) is a Rails-like framework for building VLM training data generators. It provides a convention-over-configuration approach with declarative screen definitions, reusable UI abstractions, and automatic dataset formatting.

## Development Timeline

| Date | Feature | Work |
|------|---------|------|
| 2025-12-07 | Testing | Fix test generation to respect test_distribution config |
| 2025-12-07 | Verification | Add verify.py template and update generate.sh with --verify support |
| 2025-12-06 | Performance | Parallelize sample preprocessing with ThreadPoolExecutor |
| 2025-12-05 | Data-Driven | Add AnnotationConfig and IconListTaskBase for data-driven generation |
| 2025-12-05 | Configuration | Add task_types to config.json and --exp argument to generator template |
| 2025-12-05 | Data Generation | Add get_last_name and get_first_name functions with train/test split |
| 2025-12-05 | Release | Bump version to 0.2.0 |
| 2025-12-05 | Major Refactor | Heavy refactor with annotation parser, server, scroll tasks, and distribution support |
| 2025-12-04 | Conventions | Bump version to 0.1.7 and use double-dash delimiter in dataset names |
| 2025-12-03 | Validation | Add dataset schema validation system |
| 2025-12-03 | Integration | Refactor modal_apps to use centralized config from adapters.yaml |
| 2025-12-02 | Documentation | Add agents.md with commit guidelines and CLAUDE.md symlink |
| 2025-12-02 | Release | Release v0.1.5 |
| 2025-12-02 | Utilities | Add truncate_text and config loading utilities |
| 2025-12-02 | Release | Release v0.1.4 |
| 2025-12-02 | Utilities | Add random, text, and drawing utilities |
| 2025-12-02 | Release | Release v0.1.3 |
| 2025-12-02 | Dependencies | Update uv.lock |
| 2025-12-02 | DRY Utilities | Add DRY utilities: run_generator, get_researcher_name, load_font |
| 2025-12-02 | Actions | Add double_click and right_click helpers to ToolCall |
| 2025-12-01 | Licensing | Update license to Tylt proprietary (research use only) |
| 2025-12-01 | Documentation | Add contributing section to README |
| 2025-12-01 | System Prompts | Remove compact prompt, use single system prompt |
| 2025-12-01 | System Prompts | Load system prompts from text files |
| 2025-12-01 | Documentation | Add annotations, schemas docs, and CLI improvements |
| 2025-11-28 | Configuration | Add task_distributions support to DatasetConfig |
| 2025-11-27 | Templates | Update project template for uv run and proper deps |
| 2025-11-27 | Type System | Add py.typed marker for mypy |
| 2025-11-27 | Formatting | Update annotation to <tool_call> format with prettified JSON |
| 2025-11-27 | Abstractions | Add ScrollableGrid abstraction for data grid rendering |
| 2025-11-27 | Features | Support float gaps and stratified annotations |
| 2025-11-27 | UI/UX | Move action/coords to bottom bar for cleaner crosshairs |
| 2025-11-27 | Canvas | Extend canvas height for annotation prompt bar |
| 2025-11-27 | Testing | Add test image annotation support |
| 2025-11-27 | Abstractions | Add Button abstraction for UI buttons |
| 2025-11-27 | Abstractions | Add Canvas/Region abstraction for screen composition |
| 2025-11-27 | Abstractions | Add Icon abstraction for clickable UI icons |
| 2025-11-27 | Geometry | Add natural tolerance calculation to GridGeometry |
| 2025-11-27 | Abstractions | Add Grid abstraction for UI grids |
| 2025-11-27 | Structure | Fix dataset output structure to match calendar project |
| 2025-11-26 | Integration | Add modal_apps and script templates for full pipeline support |
| 2025-11-26 | Evaluation | Add build_evals() method to DatasetBuilder for generating eval cases |
| 2025-11-26 | Distribution | Add LICENSE and PyPI publishing workflow |
| 2025-11-26 | Initial Release | Initial commit: CUDAG framework for VLM training data generation |

## Feature Categories

### Core Framework (4 features)
- Rails-like MVC pattern (Screen, State, Renderer, Task, Model)
- DatasetBuilder pattern for reusable generators
- Convention-over-configuration approach
- CLI framework with `cudag new` scaffolding

### UI Abstractions (6 features)
- Canvas/Region abstraction for screen composition
- Grid abstraction with natural tolerance calculation
- ScrollableGrid for data grid rendering
- Button abstraction for clickable UI elements
- Icon abstraction for UI icons
- Geometry utilities for layout calculations

### Data Generation (6 features)
- Domain model definitions with field types
- Random data utilities (choose, date_in_range, amount, weighted_choice)
- Text utilities (measure, center, wrap, truncate)
- Name generators with train/test split
- Annotation-driven data generation (IconListTaskBase)
- Stratified sampling with task_distributions

### Dataset Schema (5 features)
- Tool call format with <tool_call> wrapper
- Training record schema (JSONL with conversations)
- Test record schema (test.json)
- RU coordinate system (normalized to [0, 1000])
- Schema validation system with detailed error reporting

### Integration & Infrastructure (7 features)
- Modal integration (upload_dataset.py, training.py, inference.py)
- Centralized adapter config (adapters.yaml)
- System prompt management (loaded from text files)
- Template generation (cudag new)
- Verification infrastructure (verify.py template)
- Double-dash delimiter naming convention (prefix--user--timestamp)
- Parallel preprocessing with ThreadPoolExecutor (6x speedup)

### Configuration (4 features)
- YAML-based dataset configuration
- Task distributions for sample type control
- Test generation configuration
- Annotation configuration

### Developer Experience (5 features)
- DRY utilities (run_generator, get_researcher_name, load_font)
- Code quality enforcement (ruff, mypy, radon)
- Comprehensive documentation (README, SCHEMAS, DATASET_SCHEMA)
- PyPI distribution support
- Type system support (py.typed marker)

## Key Metrics

- **Total Commits:** 44
- **Development Period:** 12 days (November 26 - December 7, 2025)
- **Version:** 0.2.0
- **Major Abstractions:** 6 (Canvas, Region, Grid, ScrollableGrid, Button, Icon)
- **Utility Modules:** 5 (random, text, drawing, config, fonts)
- **Schema Definitions:** 3 (tool_call, training_record, test_record)

## Impact

CUDAG reduces generator development from ~800 lines of boilerplate to ~200 lines of domain-specific code. All 9 screen generators in the ClaimHawk platform use CUDAG, producing 40,000+ training samples across calendar, claim-window, appointment, login, desktop, chart, account, and workflow screens.

### Code Reduction Examples
- **Boilerplate eliminated:** run_generator() handles argument parsing, config loading, dataset naming
- **Renderer simplified:** BaseRenderer provides asset loading, metadata building, coordinate normalization
- **Task templates:** BaseTask standardizes sample generation, image saving, tool call formatting
- **UI abstractions:** Grid, Button, Icon reduce 100+ lines per generator to declarative definitions

### Framework Features
- **Declarative screens:** Screen class with typed region definitions
- **Type safety:** Full mypy strict compliance with py.typed marker
- **Testing:** Automatic test set generation with configurable tolerance
- **Validation:** Schema validation catches format errors before training
- **Reproducibility:** Seeded random generation for deterministic datasets

---

## AI-Assisted Development

CUDAG was built by 1 developer + AI assistants (Claude Code). No engineering team.

### Productivity Impact

| Metric | Traditional | With AI | Multiplier |
|--------|-------------|---------|------------|
| Framework design | 2-3 weeks | 3 days | **~5x** |
| Code generation | 400 lines/day | 2,000+ lines/day | **~5x** |
| Documentation | Separate effort | Generated inline | **~10x** |

### Traditional Team Equivalent

A Rails-like framework with 44 commits across 12 days would typically require:
- 2 senior engineers @ $150k/yr for 3-4 weeks = **$17-23k**
- **Actual:** 1 developer + AI, 12 days = **$1-2k**
- **Savings: ~90%**

### Framework Multiplier Effect

CUDAG itself provides a **4x code reduction** for downstream generators. Combined with AI-assisted development:
- Traditional: 800 lines per generator × manual writing = weeks per generator
- AI-assisted: 200 lines per generator × AI pair programming = hours per generator
- **Net multiplier: ~20x faster generator development**

### Key AI Contributions

- Designed abstraction hierarchy (Canvas, Region, Grid, Button, Icon)
- Generated JSON Schema validation system
- Built annotation parser with complex coordinate scaling
- Created CLI scaffolding with `cudag new` template generation
