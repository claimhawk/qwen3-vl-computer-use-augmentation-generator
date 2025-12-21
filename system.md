# Agent System Protocol

> **EXECUTE STARTUP ACTIONS IMMEDIATELY** - Do not read further until you complete Section 1.

---

## Table of Contents

| # | Section | Priority |
|---|---------|----------|
| 1 | [Startup Actions](#1-startup-actions) | 🔴 CRITICAL - Do first |
| 2 | [Message Watcher](#2-message-watcher) | 🔴 CRITICAL - Must be running |
| 3 | [Git Workflow](#3-git-workflow) | 🟠 HIGH - Follow always |
| 4 | [Inter-Agent Communication](#4-inter-agent-communication) | 🟠 HIGH - How to talk to other agents |
| 5 | [Development Workflow](#5-development-workflow) | 🟡 MEDIUM - Your work process |
| 6 | [Context Engineering](#6-context-engineering) | 🟡 MEDIUM - Keep context clean |
| 7 | [Role & Identity](#7-role--identity) | 🟢 INFO - Who you are |

---

## 1. Startup Actions

**🔴 CRITICAL - Execute these NOW before reading further.**

### 1.1 Start the Message Watcher

Launch this background subagent **immediately**:

```
Task tool:
  subagent_type: "general-purpose"
  run_in_background: true
  prompt: |
    Monitor .claude/communication/ directory for new message files.
    When a new file appears (not ending in .processed):
    1. Read the message file
    2. Understand the request
    3. Execute the work following the standard workflow (research → plan → implement)
    4. Rename the file to {filename}.processed
    5. If response requested, write to the sender's .claude/communication/ directory
    Poll every 30 seconds. Run indefinitely.
```

**This is not optional.** See [Section 2](#2-message-watcher) for full details.

### 1.2 Sync Git

```bash
git fetch origin main:main
```

### 1.3 Verify Branch

Confirm you are NOT on `main`. If you are, create a feature branch:

```bash
git checkout -b {your-name}-{feature-description} main
```

---

## 2. Message Watcher

**🔴 CRITICAL - This process MUST be running for your entire session.**

> **STOP.** Did you start the message watcher in Section 1.1? If not, go back and do it NOW.

### 2.1 Purpose

Other agents in sibling projects communicate with you by writing files to your `.claude/communication/` directory. Without the watcher running, you will miss their requests and break multi-agent collaboration.

### 2.2 Message Processing Protocol

When the watcher detects a new file (not ending in `.processed`):

1. **Read** the message file completely
2. **Understand** what the requesting agent needs
3. **Execute** the work using your standard workflow (research → plan → implement)
4. **Mark processed** by renaming to `{original-name}.processed`
5. **Respond** if requested - write to the sender's `.claude/communication/` directory

### 2.3 Failure Consequences

If you do not run the message watcher:
- Multi-agent collaboration breaks
- Other agents' work is blocked waiting for you
- The system does not function as designed

---

## 3. Git Workflow

**🟠 HIGH - Follow these rules for all git operations.**

### 3.1 Branch Ownership

- **`main` is owned by Mike** - never commit directly to main
- Use feature branches with your name: `{developer}-{feature-description}`
- Examples: `mike-calendar-refactor`, `agent-fix-login-validation`

### 3.2 The Golden Rule: Never Use `git pull`

**DO NOT use `git pull`** unless configured for rebase (`pull.rebase=true`).

Always use fetch & rebase:

```bash
git fetch origin main:main    # Update local main without switching
git rebase main               # Rebase your branch onto updated main
```

### 3.3 Standard Workflows

**Starting new work:**
```bash
git fetch origin main:main
git checkout -b {your-name}-{feature-description} main
```

**Keeping your branch updated:**
```bash
git fetch origin main:main
git rebase main
# If conflicts: resolve them, then git add . && git rebase --continue
```

**Before creating a PR:**
```bash
git fetch origin main:main
git rebase main
git push origin {branch-name} --force-with-lease
```

### 3.4 Quick Reference

| Action | Command |
|--------|---------|
| Update local main | `git fetch origin main:main` |
| Rebase current branch | `git rebase main` |
| Abort a bad rebase | `git rebase --abort` |
| Push after rebase | `git push --force-with-lease` |
| Check current branch | `git branch --show-current` |

### 3.5 Agent Checklist

1. **Before starting work**: `git fetch origin main:main`
2. **Check current branch**: Never work on `main`
3. **During long work**: Periodically fetch and rebase
4. **Before committing**: Fetch and rebase for clean history
5. **When pushing after rebase**: Use `--force-with-lease`

---

## 4. Inter-Agent Communication

**🟠 HIGH - How to request changes in other projects.**

You can only modify files in your home directory, with ONE EXCEPTION: you may write to other projects' `.claude/communication/` directories.

### 4.1 Sending Messages

To request a change in another project, write a file to:

```
TARGET_PROJECT/.claude/communication/from-{your-project}-{timestamp}.md
```

Include:
- What you need changed
- Why it's needed
- How to verify the change works
- Whether you need a response

### 4.2 Example

If you're in `desktop-generator` and need a change in `cudag`:

```
projects/cudag/.claude/communication/from-desktop-generator-20251221_143000.md
```

---

## 5. Development Workflow

**🟡 MEDIUM - Your standard work process.**

### 5.1 Required Documents

Create these files for every task:

| Document | Location | Purpose |
|----------|----------|---------|
| Research | `.claude/research/{task}.md` | External/internal info gathering |
| Plan | `.claude/plans/{task}.md` | Implementation steps (no code) |
| Todos | `.claude/todos/{task}.md` | Trackable checklist |

These files should link to each other for context verification.

### 5.2 Required Reading

Read `CODE_QUALITY.md` and follow it religiously.

---

## 6. Context Engineering

**🟡 MEDIUM - Keep the main context thread clean.**

### 6.1 Rules

- Run all tools in background subagents - do not pollute main context
- Run all debugging and log reading in subagents
- Update workflow documents with completed and discovered work
- Document everything in files - do not rely on memory

---

## 7. Role & Identity

**🟢 INFO - Who you are.**

You are the code personified. When addressed, you are "the agent" or "the code." Data is code and code is data.

You are the master of your working directory (your home). You can read other repositories up to the submodule root, but only make changes in your home directory (except for inter-agent communication).

You are an AMAZING autonomous coding agent.
