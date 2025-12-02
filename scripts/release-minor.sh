#!/bin/bash
# Release a new minor version of cudag
# Bumps minor version and resets patch to 0 (0.1.5 -> 0.2.0), commits, tags, and pushes
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYPROJECT="$REPO_ROOT/pyproject.toml"

cd "$REPO_ROOT"

# Ensure working directory is clean
if [[ -n $(git status --porcelain) ]]; then
    echo "Error: Working directory is not clean. Commit or stash changes first."
    exit 1
fi

# Extract current version
CURRENT_VERSION=$(grep '^version = "' "$PYPROJECT" | sed 's/version = "\([^"]*\)"/\1/')
if [ -z "$CURRENT_VERSION" ]; then
    echo "Error: Could not extract version from pyproject.toml"
    exit 1
fi

# Parse version components
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Bump minor, reset patch to 0
NEW_MINOR=$((MINOR + 1))
NEW_VERSION="$MAJOR.$NEW_MINOR.0"

echo "Releasing minor: $CURRENT_VERSION -> $NEW_VERSION"

# Update pyproject.toml
sed -i '' "s/^version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" "$PYPROJECT"

# Commit and tag
git add "$PYPROJECT"
git commit -m "Release v$NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"

echo ""
echo "Created commit and tag v$NEW_VERSION"
echo "Run 'git push && git push --tags' to publish"
