# Research: Annotation-Driven Scaffolding

## Overview

This document analyzes the gap between CUDAG's current scaffolding (which generates hardcoded generators) and the new annotation-driven pattern (demonstrated in calendar-generator). The goal is to update CUDAG scaffolding to generate generators that follow the modern pattern.

## Current Scaffolding Approach

### Files Involved
- `src/cudag/annotation/scaffold.py` - Orchestrates file generation
- `src/cudag/annotation/codegen.py` - Code generation templates
- `src/cudag/annotation/loader.py` - Parses annotation.json

### Generated Directory Structure (Current)
```
my-generator/
├── screen.py           # Hardcoded Screen class with baked-in coordinates
├── state.py            # State dataclass
├── renderer.py         # Loads assets/blanks/base.png
├── generator.py        # Main entry point
├── tasks/              # Per-task Python files
│   ├── __init__.py
│   └── click_button.py
├── assets/
│   ├── blanks/
│   │   └── base.png    # Original image
│   └── icons/
└── config/
    └── dataset.yaml
```

### Problems with Current Approach

1. **Hardcoded Coordinates**: `screen.py` bakes element positions into Python code:
   ```python
   class CalendarScreen(Screen):
       name = "calendar"
       base_image = "assets/blanks/base.png"
       size = (380, 352)

       calendar_grid = grid((1, 122, 379, 152), rows=6, cols=7)
       back_button = button((3, 56, 34, 25), label="top-back-year")
   ```

2. **No Coordinate Scaling**: Assumes generator output matches annotation image size

3. **No Runtime Loading**: Annotation data is converted to Python at scaffold time, not loaded at runtime

4. **Separate Task Files**: Each task gets its own file, increasing boilerplate

5. **Uses `assets/blanks/base.png`**: Not aligned with annotator which produces `masked.png`

## New Annotation-Driven Pattern

### Demonstrated in calendar-generator

The calendar-generator shows the modern pattern:

1. **Runtime Loading**: `screen.py` uses `AnnotationConfig.load()`:
   ```python
   from cudag.annotation import AnnotationConfig

   ANNOTATION_CONFIG = AnnotationConfig.load(_ANNOTATIONS_DIR)
   ```

2. **Coordinate Scaling**: Supports different annotation vs output sizes:
   ```python
   _ANNOTATION_SIZE = ANNOTATION_CONFIG.image_size  # (380, 352)
   _GENERATOR_SIZE = (225, 208)

   _SCALE_X = _GENERATOR_SIZE[0] / _ANNOTATION_SIZE[0]
   _SCALE_Y = _GENERATOR_SIZE[1] / _ANNOTATION_SIZE[1]
   ```

3. **Helper Functions**: Clean accessor pattern:
   ```python
   def get_grid_element() -> AnnotatedElement:
       return ANNOTATION_CONFIG.get_element_by_label("calendar")

   def get_button_center(name: str) -> tuple[int, int]:
       el = get_button_element(name)
       return scale_coord(el.center[0], el.center[1])
   ```

4. **Uses `masked.png`**: Renderer loads the annotator's masked image:
   ```python
   _MASKED_PATH = get_masked_image_path()
   self._image = Image.open(_MASKED_PATH).resize(_GENERATOR_SIZE)
   ```

5. **Task Prompts from Annotation**: Tasks use `AnnotatedTask.prompt_template`:
   ```python
   task = get_click_day_task()
   prompt = task.prompt_template.replace("[day]", str(day))
   ```

### New Directory Structure
```
my-generator/
├── screen.py           # Loads AnnotationConfig at runtime
├── state.py            # State dataclass (unchanged)
├── renderer.py         # Loads assets/annotations/masked.png
├── generator.py        # Main entry point
├── tasks/              # Task modules
│   ├── __init__.py
│   ├── click_button.py
│   └── click_day.py
├── assets/
│   └── annotations/    # NEW: annotation data directory
│       ├── annotation.json
│       ├── masked.png
│       └── original.png (optional)
└── config/
    └── dataset.yaml
```

## Comparison Matrix

| Aspect | Current Scaffolding | New Pattern |
|--------|---------------------|-------------|
| Coordinates | Hardcoded in screen.py | Loaded at runtime from annotation.json |
| Image | `assets/blanks/base.png` | `assets/annotations/masked.png` |
| Scaling | None | Supports annotation → generator size |
| Element access | `screen.my_button` attribute | `get_button_element("my-button")` function |
| Tolerance | Hardcoded or TODO | From annotation `toleranceX/Y` |
| Task prompts | Hardcoded strings | From annotation `prompt` with placeholders |
| Annotation changes | Requires regenerating scaffold | Just update annotation.json |

## Runtime Support Already in CUDAG

CUDAG already has runtime support via `src/cudag/annotation/config.py`:

- `AnnotationConfig.load(path)` - Loads annotation.json
- `AnnotatedElement` - Element with bbox, tolerance, icons
- `AnnotatedTask` - Task with prompt_template, target_element_id
- `get_element_by_label()`, `get_task_by_type()` - Accessors
- `masked_image_path`, `original_image_path` - Path properties

The runtime infrastructure exists. Only the scaffolding needs updating.

## Files to Modify

### 1. `src/cudag/annotation/scaffold.py`
- Change `assets/blanks/` to `assets/annotations/`
- Copy annotation.json, masked.png, original.png to new location
- Remove `assets/icons/` (icons stay in annotations)

### 2. `src/cudag/annotation/codegen.py`
Update all `generate_*` functions:

**`generate_screen_py()`**: Replace hardcoded Screen class with:
- Import `AnnotationConfig`
- Load config at module level
- Add coordinate scaling logic
- Provide helper functions (`get_grid_element()`, `get_button_center()`, etc.)

**`generate_renderer_py()`**: Update to:
- Load `assets/annotations/masked.png`
- Support resizing for different output sizes
- Use screen.py helpers for element positions

**`generate_generator_py()`**: Update to:
- Use new task registration pattern
- Support config.yaml parameters

**`generate_task_py()`**: Update to:
- Use screen.py helpers for coordinates
- Get prompts from AnnotatedTask
- Calculate tolerance from annotation

### 3. New: `generate_annotation_screen_py()`
Consider a separate function for annotation-driven screen.py that:
- Loads AnnotationConfig at runtime
- Provides scaling utilities
- Exports helper functions based on element types found

## Design Decisions

### 1. Backward Compatibility
Keep existing `generate_screen_py()` for projects that want the old pattern. Add new `generate_annotation_screen_py()` for annotation-driven generators.

OR: Make annotation-driven the default with a flag to use old pattern.

**Recommendation**: Make annotation-driven the default. Old pattern is deprecated.

### 2. Generator Size Configuration
Add to config/dataset.yaml:
```yaml
image:
  width: 225
  height: 208
```

Or derive from annotation.json `imageSize` with optional override.

**Recommendation**: Add optional `output_size` in dataset.yaml, default to annotation size.

### 3. Task File Strategy
Current: One file per task
New: Could consolidate related tasks

**Recommendation**: Keep one file per task for flexibility, but tasks should be simpler (using helpers from screen.py).

### 4. Grid-Specific Fields
`AnnotationConfig` doesn't expose grid rows/cols directly. calendar-generator loads raw JSON:
```python
with open(_ANNOTATIONS_DIR / "annotation.json") as f:
    _RAW_ANNOTATION = json.load(f)
```

**Recommendation**: Add `rows`, `cols`, `colWidths`, `rowHeights` to `AnnotatedElement` for grid types.

## Migration Path

1. Update `AnnotatedElement` to include grid fields (rows, cols, colWidths, rowHeights)
2. Create new codegen functions for annotation-driven pattern
3. Update `scaffold_generator()` to use new directory structure
4. Add `--legacy` flag to `cudag new` for old pattern (if needed)
5. Update documentation

## Test Strategy

1. Create test annotation.json fixture
2. Scaffold new generator
3. Verify all files use runtime loading
4. Run generated generator to produce dataset
5. Validate dataset conforms to schema
