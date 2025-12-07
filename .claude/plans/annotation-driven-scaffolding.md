# Plan: Update CUDAG Scaffolding to Annotation-Driven Pattern

## Objective

Update CUDAG's scaffolding system to generate generators that use the annotation-driven pattern (runtime loading via `AnnotationConfig`) instead of the current hardcoded pattern.

## Prerequisites

- Research document: `.claude/research/annotation-driven-scaffolding.md`
- Reference implementation: `calendar-generator/screen.py`

## Implementation Steps

### Phase 1: Extend AnnotatedElement for Grid Support

**File**: `src/cudag/annotation/config.py`

1. Add grid-specific fields to `AnnotatedElement`:
   ```python
   rows: int = 0
   cols: int = 0
   col_widths: list[float] = field(default_factory=list)
   row_heights: list[float] = field(default_factory=list)
   ```

2. Update `_parse_element()` to extract grid fields:
   ```python
   rows=el.get("rows", 0),
   cols=el.get("cols", 0),
   col_widths=el.get("colWidths", []),
   row_heights=el.get("rowHeights", []),
   ```

### Phase 2: Update Directory Structure in scaffold.py

**File**: `src/cudag/annotation/scaffold.py`

1. Change asset paths:
   - `assets/blanks/base.png` → `assets/annotations/original.png`
   - `assets/blanks/masked.png` → `assets/annotations/masked.png`
   - Copy annotation.json to `assets/annotations/`

2. Update `scaffold_generator()`:
   ```python
   # Create directory structure
   (project_dir / "tasks").mkdir(exist_ok=True)
   (project_dir / "assets" / "annotations").mkdir(parents=True, exist_ok=True)
   (project_dir / "config").mkdir(exist_ok=True)

   # Save annotation.json
   annotation_json = project_dir / "assets" / "annotations" / "annotation.json"
   annotation_json.write_text(json.dumps(annotation.to_dict(), indent=2))

   # Save images
   if original_image:
       (project_dir / "assets" / "annotations" / "original.png").write_bytes(original_image)
   if masked_image:
       (project_dir / "assets" / "annotations" / "masked.png").write_bytes(masked_image)
   ```

3. Add `to_dict()` method to `ParsedAnnotation` (or pass raw dict through)

### Phase 3: Rewrite generate_screen_py()

**File**: `src/cudag/annotation/codegen.py`

Replace `generate_screen_py()` to emit runtime-loading code:

```python
def generate_screen_py(annotation: ParsedAnnotation) -> str:
    """Generate screen.py with runtime annotation loading."""

    # Identify element types present
    has_grid = any(el.region_type == "grid" for el in annotation.elements)
    has_buttons = any(el.region_type == "button" for el in annotation.elements)
    has_text = any(el.region_type == "text" for el in annotation.elements)

    # Generate helper functions based on element types
    helpers = []
    if has_grid:
        helpers.append(_generate_grid_helpers())
    if has_buttons:
        helpers.append(_generate_button_helpers())
    if has_text:
        helpers.append(_generate_text_helpers())

    return SCREEN_TEMPLATE.format(
        screen_name=annotation.screen_name,
        image_size=annotation.image_size,
        helpers="\n\n".join(helpers),
    )
```

Template structure:
```python
SCREEN_TEMPLATE = '''...
from cudag.annotation import AnnotationConfig

_ANNOTATIONS_DIR = Path(__file__).parent / "assets" / "annotations"
ANNOTATION_CONFIG = AnnotationConfig.load(_ANNOTATIONS_DIR)

# Coordinate scaling
_ANNOTATION_SIZE = ANNOTATION_CONFIG.image_size
_GENERATOR_SIZE = {image_size}  # Override in config if needed
_SCALE_X = _GENERATOR_SIZE[0] / _ANNOTATION_SIZE[0]
_SCALE_Y = _GENERATOR_SIZE[1] / _ANNOTATION_SIZE[1]

def scale_coord(x: int | float, y: int | float) -> tuple[int, int]: ...
def scale_bbox(bbox: tuple[int, int, int, int]) -> tuple[int, int, int, int]: ...
def scale_tolerance(tol_x: int, tol_y: int) -> tuple[int, int]: ...

{helpers}

def get_masked_image_path() -> Path: ...
'''
```

### Phase 4: Update generate_renderer_py()

**File**: `src/cudag/annotation/codegen.py`

Update to:
1. Load from `assets/annotations/masked.png`
2. Use `get_masked_image_path()` from screen module
3. Support image resizing

```python
RENDERER_TEMPLATE = '''...
from screen import get_masked_image_path, _GENERATOR_SIZE

class {renderer_class}(BaseRenderer[{state_class}]):
    def __init__(self) -> None:
        super().__init__()
        masked_path = get_masked_image_path()
        self._base_image = Image.open(masked_path).resize(_GENERATOR_SIZE)

    def render(self, state: {state_class}) -> tuple[Image.Image, dict[str, Any]]:
        image = self._base_image.copy()
        # Dynamic rendering based on state...
        return image, metadata
'''
```

### Phase 5: Update generate_task_py()

**File**: `src/cudag/annotation/codegen.py`

Update tasks to:
1. Import helpers from screen.py
2. Get prompts from annotation
3. Calculate tolerance from annotation

```python
TASK_TEMPLATE = '''...
from screen import (
    get_button_center,
    get_button_tolerance,
    get_button_task,
    scale_coord,
)

class {task_class}(BaseTask):
    def generate_sample(self, ctx: TaskContext) -> TaskSample:
        # Get coordinates from annotation
        pixel_coords = get_button_center("{button_name}")
        tolerance = get_button_tolerance("{button_name}")

        # Get prompt from annotation
        task = get_button_task("{button_name}")
        prompt = task.prompt_template

        ...
'''
```

### Phase 6: Update generate_config_yaml()

Add output size configuration:

```yaml
# Image output settings
image:
  # Output size (defaults to annotation size if not specified)
  # width: 225
  # height: 208

# Task generation
tasks:
  click_day: 1000
  click_button: 100
```

### Phase 7: Update CLI (if needed)

**File**: `src/cudag/cli.py` (if exists)

Ensure `cudag new` command uses updated scaffolding.

### Phase 8: Testing

1. Create test annotation fixture with grid, buttons, text elements
2. Run scaffold on fixture
3. Verify generated code:
   - `screen.py` loads annotation at runtime
   - `renderer.py` uses masked.png
   - Tasks use screen.py helpers
4. Run generated generator
5. Validate output dataset schema

## Files Modified

| File | Changes |
|------|---------|
| `src/cudag/annotation/config.py` | Add grid fields to AnnotatedElement |
| `src/cudag/annotation/scaffold.py` | New directory structure, copy annotation.json |
| `src/cudag/annotation/codegen.py` | Rewrite all generate_* functions |
| `src/cudag/annotation/loader.py` | Add `to_dict()` if needed |

## Validation Criteria

1. Scaffolded generator runs without modification
2. Generated dataset passes `cudag validate`
3. No hardcoded coordinates in generated code
4. Changing annotation.json updates generator behavior without regenerating scaffold

## Rollback Plan

If issues arise, the existing codegen functions are preserved. New functions can be named `generate_annotation_screen_py()` etc. to maintain backward compatibility until stable.
