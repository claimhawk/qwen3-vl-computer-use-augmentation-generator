---
name: block-secrets-in-code
enabled: true
event: file
action: block
conditions:
  - field: content
    operator: regex_match
    pattern: (sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|glpat-[a-zA-Z0-9-]{20,}|AKIA[0-9A-Z]{16})
---

**SECRET DETECTED - BLOCKED**

A potential API key or secret token was detected in your code:
- OpenAI API key (sk-...)
- GitHub token (ghp_/gho_...)
- GitLab token (glpat-...)
- AWS access key (AKIA...)

**Action Required:**
1. Remove the secret from the code immediately
2. Use environment variables instead: `os.environ.get("SECRET_NAME")`
3. Add the secret to `.env` file (ensure it's in `.gitignore`)
4. If accidentally committed, rotate the secret immediately
