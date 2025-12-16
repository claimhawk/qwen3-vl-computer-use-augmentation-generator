#!/usr/bin/env bash
# Copyright (c) 2025 Tylt LLC. All rights reserved.
# Build and deploy cudag to PyPI
#
# Usage:
#   ./scripts/build-deploy.sh          # Build and deploy current version
#   ./scripts/build-deploy.sh patch    # Bump patch version, build, deploy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Bump version if requested
if [[ "${1:-}" == "patch" ]]; then
    CURRENT=$(grep '^version' pyproject.toml | cut -d'"' -f2)
    IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"
    NEW_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
    sed -i '' "s/version = \"$CURRENT\"/version = \"$NEW_VERSION\"/" pyproject.toml
    echo "Bumped version: $CURRENT -> $NEW_VERSION"
fi

# Load environment
if [[ -f .env ]]; then
    source .env
fi

# Check for PyPI token
if [[ -z "${UV_PUBLISH_PASSWORD:-}" ]]; then
    echo "Error: UV_PUBLISH_PASSWORD not set in .env"
    exit 1
fi

# Sync system prompt (replace symlink with actual file for packaging)
PROMPT_FILE="$PROJECT_DIR/src/cudag/prompts/SYSTEM_PROMPT.txt"
SYSTEM_PROMPT_SRC="/Users/michaeloneal/development/claimhawk/projects/system-prompt/SYSTEM_PROMPT.txt"

if [[ -L "$PROMPT_FILE" ]]; then
    rm "$PROMPT_FILE"
fi
cp "$SYSTEM_PROMPT_SRC" "$PROMPT_FILE"
echo "Synced SYSTEM_PROMPT.txt"

# Clean and build
rm -rf dist/
python3 -m build
echo "Built package"

# Upload to PyPI
python3 -m twine upload dist/* --username __token__ --password "$UV_PUBLISH_PASSWORD"

# Get version and tag
VERSION=$(grep '^version' pyproject.toml | cut -d'"' -f2)
TAG="v$VERSION"

# Git operations (skip if not a git repo or in submodule with issues)
if git rev-parse --git-dir >/dev/null 2>&1; then
    # Commit version bump if changed
    if ! git diff --quiet pyproject.toml 2>/dev/null; then
        git add pyproject.toml
        git commit -m "Bump version to $VERSION"
    fi

    # Tag and push
    git tag -a "$TAG" -m "Release $VERSION" 2>/dev/null || echo "Tag $TAG may already exist"
    git push origin HEAD --tags 2>/dev/null || echo "Git push skipped (may need manual push)"
else
    echo "Git operations skipped (not a git repo)"
fi

echo "Deployed cudag==$VERSION to PyPI and tagged $TAG"
