---
name: warn-hardcoded-passwords
enabled: true
event: file
action: block
conditions:
  - field: content
    operator: regex_match
    pattern: (password|passwd|pwd)\s*[=:]\s*["'][^"']{8,}["']
  - field: file_path
    operator: regex_match
    pattern: \.(py|ts|tsx|js|jsx|yaml|yml|json)$
---

**Potential Hardcoded Password Detected**

A string that looks like a hardcoded password was found.

**If this is a real credential:**
1. Remove it immediately
2. Use environment variables or a secrets manager
3. Rotate the password if it was committed

**If this is test/mock data:**
- Consider using clearly fake values like "test-password-placeholder"
- Add a comment explaining it's mock data
