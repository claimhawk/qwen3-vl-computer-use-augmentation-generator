---
name: enforce-python-quality
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.py$
  - field: content
    operator: regex_not_match
    pattern: ^# Copyright
---

**Python Quality Reminder**

When modifying Python files, ensure:

1. **Copyright header** - All files must start with:
   ```python
   # Copyright (c) 2025 Tylt LLC. All rights reserved.
   ```

2. **Type hints** - All functions require type annotations

3. **Pre-commit checks** - Run before committing:
   ```bash
   ./scripts/pre-commit.sh
   ```

4. **Quality standards**:
   - Max cyclomatic complexity: 10
   - Max function length: 50-60 lines
   - Pass ruff, mypy, and radon checks
