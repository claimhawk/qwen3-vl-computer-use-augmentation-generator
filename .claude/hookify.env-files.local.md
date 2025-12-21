---
name: block-env-commits
enabled: true
event: bash
pattern: git add.*\.env(?!\.example)
action: block
---

**BLOCKED: Attempting to commit .env file**

`.env` files contain secrets and should NEVER be committed to git.

**Instead:**
1. Ensure `.env` is in `.gitignore`
2. Create a `.env.example` with placeholder values
3. Document required environment variables in README

**If you need to share env vars:**
- Use a secrets manager (1Password, Vault, etc.)
- Use Modal secrets: `modal secret create`
- Share securely via encrypted channels
