---
name: block-env-fallbacks
enabled: true
event: file
action: block
conditions:
  - field: content
    operator: regex_match
    pattern: (os\.environ\.get|process\.env\.\w+\s*\|\|).*https?://
  - field: file_path
    operator: regex_match
    pattern: \.(py|ts|tsx|js|jsx)$
---

**BLOCKED: Environment variable fallback with URL detected**

You are using a fallback default for an environment variable:
```
os.environ.get("VAR", "https://...")  # Python
process.env.VAR || "https://..."       # TypeScript
```

**Fallbacks hide bugs!** If the env var isn't set, the code should FAIL immediately rather than silently using a fallback.

**Fix:**
```python
# Python - will raise KeyError if not set
ENDPOINT = os.environ["VAR_NAME"]
```

```typescript
// TypeScript - will throw if not set
const ENDPOINT = process.env.VAR_NAME;
if (!ENDPOINT) throw new Error("VAR_NAME environment variable required");
```

**Then document in .env.example:**
```
VAR_NAME=https://your-endpoint-here.modal.run
```
