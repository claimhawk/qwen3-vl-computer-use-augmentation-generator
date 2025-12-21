# Implementation Plan: Manifest Format Support

**Date**: 2025-12-21
**Target File**: `src/cudag/annotation/config.py`
**Target Method**: `AnnotationConfig.load()`

## Overview

Add v2.0 manifest format support to `AnnotationConfig.load()` while maintaining full backward compatibility with legacy format.

## Changes Required

### 1. Update `AnnotationConfig.load()` method

**Location**: Lines 301-321

**Current implementation**: Direct load and parse of `annotation.json`

**New implementation**:
1. Load `annotation.json`
2. Check if `data.get("type") == "manifest"`
3. If manifest:
   - Validate `screens` array exists and is non-empty
   - Extract first screen from `screens[0]`
   - Construct path to screen's annotation: `annotations_dir / screen["name"] / "annotation.json"`
   - Load screen annotation file
   - Parse screen data
   - Set `annotations_dir` to screen subfolder (NOT root)
4. If legacy:
   - Parse data directly (existing behavior)
   - Set `annotations_dir` to provided path (existing behavior)

**Pseudocode**:
```python
@classmethod
def load(cls, annotations_dir: Path | str) -> "AnnotationConfig":
    # Convert to Path
    annotations_dir = Path(annotations_dir)
    json_path = annotations_dir / "annotation.json"

    # Check existence
    if not json_path.exists():
        raise FileNotFoundError(f"annotation.json not found in {annotations_dir}")

    # Load root file
    with open(json_path) as f:
        data = json.load(f)

    # Format detection
    if data.get("type") == "manifest":
        # Manifest format (v2.0)
        screens = data.get("screens", [])

        if not screens:
            raise ValueError("Manifest contains no screens")

        # Load first screen
        first_screen = screens[0]
        screen_name = first_screen["name"]
        screen_path = annotations_dir / screen_name / "annotation.json"

        if not screen_path.exists():
            raise FileNotFoundError(
                f"Screen annotation not found: {screen_path}"
            )

        with open(screen_path) as f:
            screen_data = json.load(f)

        config = cls._parse_dict(screen_data)
        config.annotations_dir = annotations_dir / screen_name
        return config

    # Legacy format - parse directly
    config = cls._parse_dict(data)
    config.annotations_dir = annotations_dir
    return config
```

**Line count estimate**: ~35 lines (under 50-line limit)

**Cyclomatic complexity**: 4 (under 10 limit)
- 1 base
- +1 for `if not json_path.exists()`
- +1 for `if data.get("type") == "manifest"`
- +1 for `if not screens`
- +1 for `if not screen_path.exists()`

### 2. Update `_parse_dict()` to support both field names

**Location**: Lines 324-337

**Current code** (line 332):
```python
screen_name=data.get("screenName", "untitled"),
```

**New code**:
```python
screen_name=data.get("name") or data.get("screenName", "untitled"),
```

**Rationale**:
- New manifest format uses `name` field
- Legacy format uses `screenName` field
- This handles both gracefully

### 3. Add docstring updates

Update `load()` docstring to document both formats:

```python
"""Load annotation config from a directory.

Supports two formats:
1. Legacy format: annotation.json contains screen data directly
2. Manifest format (v2.0): annotation.json is a manifest pointing to
   screen subfolders, each with its own annotation.json

Args:
    annotations_dir: Path to annotations directory containing annotation.json

Returns:
    Loaded AnnotationConfig instance for the first/only screen

Raises:
    FileNotFoundError: If annotation.json or screen subfolder not found
    ValueError: If manifest contains no screens
"""
```

## Error Messages

### New error messages:
1. `"Manifest contains no screens"` - when `screens` array is empty
2. `f"Screen annotation not found: {screen_path}"` - when screen subfolder annotation missing

### Existing error messages (unchanged):
1. `f"annotation.json not found in {annotations_dir}"`

## Testing Strategy

### Manual Testing

Test with calendar-generator (uses manifest format):
```bash
cd /Users/michaeloneal/development/claimhawk/projects/sl/generators/calendar-generator
uv run --python 3.12 python -c "from screen import ANNOTATION_CONFIG; print(f'Screen: {ANNOTATION_CONFIG.screen_name}, Dir: {ANNOTATION_CONFIG.annotations_dir}')"
```

Expected output:
```
Screen: calendar, Dir: /path/to/assets/annotations/calendar
```

### Backward Compatibility Test

Create test script to verify legacy format still works:
```python
# test_legacy_format.py
from pathlib import Path
from cudag.annotation import AnnotationConfig

# Would need a legacy format annotation.json for this
# For now, verify no existing generators break
```

### Edge Cases to Handle

1. Empty screens array: Should raise `ValueError`
2. Screen subfolder doesn't exist: Should raise `FileNotFoundError`
3. Screen annotation.json doesn't exist: Should raise `FileNotFoundError`
4. Malformed JSON: Will raise `json.JSONDecodeError` (existing behavior)

## Dependencies

None - all required modules already imported:
- `json` (already imported)
- `Path` (already imported)

## Code Quality Checklist

- [ ] Type hints present (all parameters and return values)
- [ ] Docstring updated
- [ ] Maximum function length < 50 lines
- [ ] Cyclomatic complexity < 10
- [ ] Backward compatible (legacy format works)
- [ ] Error messages are clear
- [ ] No breaking changes to public API

## Rollback Plan

If issues arise:
1. Git revert the commit
2. File shows up as single, isolated change
3. No dependencies on other modules

## Future Enhancements (Out of Scope)

1. Add `load_screen(annotations_dir, screen_name)` for explicit screen selection
2. Add `load_all_screens(annotations_dir)` to load multiple screens
3. Add manifest version validation
4. Add multi-screen warnings

## Implementation Order

1. Update `_parse_dict()` to support `name` field (1 line change)
2. Update `load()` method with format detection (30 lines added)
3. Update docstring (documentation)
4. Manual testing with calendar-generator
5. Verify no existing generators break

## Estimated Impact

- Files modified: 1 (`src/cudag/annotation/config.py`)
- Lines added: ~35
- Lines modified: 1
- Breaking changes: 0
- Generators affected: All (but backward compatible)
