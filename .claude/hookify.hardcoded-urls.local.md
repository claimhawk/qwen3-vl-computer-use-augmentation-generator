---
name: warn-hardcoded-modal-urls
enabled: true
event: file
action: block
conditions:
  - field: content
    operator: regex_match
    pattern: https://claimhawk--[a-z-]+\.modal\.run
  - field: file_path
    operator: regex_match
    pattern: \.(py|ts|tsx|js|jsx)$
---

**Hardcoded Modal URL Detected**

You're adding a hardcoded Modal deployment URL. These URLs should use environment variables:

**Python:**
```python
import os
ENDPOINT = os.environ.get("ENDPOINT_NAME", "https://fallback-url.modal.run")
```

**TypeScript/JavaScript:**
```typescript
const ENDPOINT = process.env.ENDPOINT_NAME || "https://fallback-url.modal.run";
```

This ensures:
- Easy switching between dev/staging/production
- No secrets in code
- Simpler deployment configuration
