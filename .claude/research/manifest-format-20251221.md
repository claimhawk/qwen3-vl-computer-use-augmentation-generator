# Research: Manifest Format Support for AnnotationConfig

**Date**: 2025-12-21
**Agent**: CUDAG Implementation Agent
**Task**: Add v2.0 manifest format support to `AnnotationConfig.load()`

## Context

The annotator tool has been updated to save annotations in a manifest format (v2.0) where:
- Root `annotation.json` is a manifest listing all screens
- Each screen's full annotation is in `{screenName}/annotation.json`

The CUDAG `AnnotationConfig.load()` method currently assumes a flat structure where `annotation.json` contains the full screen configuration directly.

## Current Implementation Analysis

### File: `src/cudag/annotation/config.py`

**Current `load()` method (lines 301-321)**:
```python
@classmethod
def load(cls, annotations_dir: Path | str) -> "AnnotationConfig":
    annotations_dir = Path(annotations_dir)
    json_path = annotations_dir / "annotation.json"

    if not json_path.exists():
        raise FileNotFoundError(f"annotation.json not found in {annotations_dir}")

    with open(json_path) as f:
        data = json.load(f)

    config = cls._parse_dict(data)
    config.annotations_dir = annotations_dir
    return config
```

**Key observations**:
1. Simple, direct approach - loads `annotation.json` and parses it immediately
2. Sets `annotations_dir` to the provided path
3. No format detection or versioning logic
4. `_parse_dict()` expects screen-level data with `elements`, `tasks`, `imageSize`, etc.

### Legacy Format Structure

Based on `_parse_dict()` expectations (lines 324-337):
```json
{
  "screenName": "calendar",
  "imageSize": [380, 352],
  "imagePath": "original.jpg",
  "elements": [...],
  "tasks": [...]
}
```

This is the "screen document" format - contains all the UI element and task data directly.

### New Manifest Format Structure

**Root manifest** (`assets/annotations/annotation.json`):
```json
{
  "version": "2.0",
  "type": "manifest",
  "screens": [
    {"id": "screen_123", "name": "calendar"}
  ]
}
```

**Per-screen document** (`assets/annotations/calendar/annotation.json`):
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

Note: The per-screen document uses `name` instead of `screenName`.

## Format Detection Strategy

### Discriminator Field: `type`

The manifest format includes a `type: "manifest"` field. This is the most reliable discriminator:
- Manifest format: `data.get("type") == "manifest"`
- Legacy format: No `type` field present

### Why `type` is better than other fields

Alternative discriminators considered:
1. **Presence of `screens` field**: Could conflict if legacy format adds a `screens` field in the future
2. **Presence of `version` field**: Version could be added to legacy format
3. **Absence of `elements` field**: Too implicit, could cause confusion

Decision: Use `type: "manifest"` as the primary discriminator.

## Path Resolution

### Legacy Format
- `annotations_dir` points directly to the screen folder
- Images at `{annotations_dir}/original.png`, `{annotations_dir}/masked.png`

### Manifest Format
- Root `annotations_dir` contains the manifest
- Screen subfolder at `{annotations_dir}/{screenName}/`
- Images at `{annotations_dir}/{screenName}/original.png`, etc.

### Impact on `annotations_dir` Property

The `AnnotationConfig.annotations_dir` property is used by:
- `masked_image_path` (line 525): `self.annotations_dir / "masked.png"`
- `original_image_path` (line 532): `self.annotations_dir / "original.png"`

For manifest format, `annotations_dir` MUST point to the screen subfolder, not the root manifest folder.

## Field Name Discrepancy

Legacy format uses `screenName`, new format uses `name`.

Analysis:
- `_parse_dict()` line 332: `screen_name=data.get("screenName", "untitled")`
- New format provides `name` field
- Need to handle both field names for compatibility

## Multi-Screen Considerations

The annotator supports multiple screens in a single manifest. However:
1. Current generators are single-screen
2. `AnnotationConfig` represents a single screen's configuration
3. For now, loading the first screen is sufficient

Future enhancement: Add `load_screen(annotations_dir, screen_name)` method for explicit screen selection.

## Error Handling

Need to handle:
1. Manifest with no screens
2. Screen subfolder doesn't exist
3. Screen annotation.json doesn't exist
4. Malformed manifest structure

## Backward Compatibility Requirements

1. Legacy format (no `type` field) must continue working
2. No changes to existing generator code required
3. No changes to `_parse_dict()` required
4. Path resolution must work for both formats

## Implementation Constraints

From code quality requirements:
- Maximum function length: 50-60 lines
- Maximum cyclomatic complexity: 10
- Type hints required
- Error messages must be clear

Current `load()` is 11 lines. Adding manifest support will increase this, but should stay well under 50 lines.

## Risks and Mitigations

### Risk 1: Breaking existing generators
**Mitigation**: Default to legacy behavior when `type` field is absent

### Risk 2: Path confusion
**Mitigation**: Clear documentation of `annotations_dir` semantics in both formats

### Risk 3: Field name conflicts
**Mitigation**: Support both `screenName` and `name` in `_parse_dict()`

### Risk 4: Multi-screen confusion
**Mitigation**: Document that `load()` returns first screen; add `load_screen()` for explicit selection later if needed

## Open Questions

1. Should we validate manifest `version` field?
   - **Decision**: No validation for now - just check `type: "manifest"`
   - Rationale: Version may evolve; `type` is sufficient discriminator

2. Should we add a warning when loading from manifest with multiple screens?
   - **Decision**: No warning for now
   - Rationale: Annotator currently creates single-screen manifests; avoid noise

3. Should `_parse_dict()` be updated to accept both `screenName` and `name`?
   - **Decision**: Yes, for robustness
   - Implementation: `screen_name=data.get("name") or data.get("screenName", "untitled")`

## Conclusion

The implementation is straightforward:
1. Add format detection via `type: "manifest"` check
2. If manifest, load first screen from subfolder
3. Adjust `annotations_dir` to point to screen subfolder
4. Update `_parse_dict()` to accept `name` field
5. Maintain full backward compatibility

No architectural changes needed. The existing structure supports this enhancement cleanly.
