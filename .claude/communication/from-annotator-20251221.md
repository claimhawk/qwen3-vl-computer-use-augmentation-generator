# Request: Update AnnotationConfig to Support Manifest Format

**From**: annotator
**Date**: 2025-12-21
**Priority**: High
**Status**: Pending

## Summary

The annotator now saves annotations in a manifest format (v2.0) where:
- Root `annotation.json` is a manifest pointing to screen subfolders
- Each screen's full annotation is in `{screenName}/annotation.json`

cudag's `AnnotationConfig.load()` needs to be updated to support this format while maintaining backward compatibility.

## New Manifest Format (v2.0)

Root `assets/annotations/annotation.json`:
```json
{
  "version": "2.0",
  "type": "manifest",
  "screens": [
    {"id": "screen_123", "name": "calendar"}
  ]
}
```

Per-screen `assets/annotations/{screenName}/annotation.json`:
```json
{
  "id": "screen_123",
  "name": "calendar",
  "imageSize": [380, 352],
  "imagePath": "original.jpg",
  "elements": [...],
  "tasks": [...]
}
```

## Required Changes

### File: `src/cudag/annotation/config.py`

Update `AnnotationConfig.load()` to:

1. Read `annotation.json`
2. Check if `parsed.get("type") == "manifest"`
3. If manifest format:
   - Load each screen from its subfolder
   - Return an `AnnotationConfig` for the first/only screen (for single-screen generators)
   - Or provide a new method `load_screen(name)` for multi-screen access
4. If legacy format (no `type` field): handle as before

### Suggested Implementation

```python
@classmethod
def load(cls, annotations_dir: Path | str) -> "AnnotationConfig":
    annotations_dir = Path(annotations_dir)
    json_path = annotations_dir / "annotation.json"

    if not json_path.exists():
        raise FileNotFoundError(f"annotation.json not found in {annotations_dir}")

    with open(json_path) as f:
        data = json.load(f)

    # Check for manifest format (v2.0)
    if data.get("type") == "manifest":
        screens = data.get("screens", [])
        if not screens:
            raise ValueError("Manifest contains no screens")

        # Load first screen (for single-screen generators)
        first_screen = screens[0]
        screen_path = annotations_dir / first_screen["name"] / "annotation.json"

        if not screen_path.exists():
            raise FileNotFoundError(f"Screen annotation not found: {screen_path}")

        with open(screen_path) as f:
            screen_data = json.load(f)

        config = cls._parse_dict(screen_data)
        config.annotations_dir = annotations_dir / first_screen["name"]
        return config

    # Legacy format - parse directly
    config = cls._parse_dict(data)
    config.annotations_dir = annotations_dir
    return config
```

## Testing

After implementing, verify with calendar-generator:
```bash
cd projects/sl/generators/calendar-generator
uv run --python 3.12 python -c "from screen import ANNOTATION_CONFIG; print(ANNOTATION_CONFIG.screen_name)"
```

Expected output: `calendar`

## Backward Compatibility

- Legacy `annotation.json` (without `type` field) continues to work unchanged
- Manifest format detected by presence of `type: "manifest"` field
- No breaking changes to existing generators
