#!/usr/bin/env bash
set -euo pipefail

# Sync the hunt prediction ingestion package into a GitHub repository.
# Usage:
#   ./sync_to_github.sh UTAHOGA/HUNT-PLANNER data/ingestion/utah/2024 ingest/utah-2024-hunt-data main
#
# Requirements:
#   - git
#   - GitHub CLI authenticated with push access (`gh auth login`) OR an HTTPS credential/token configured for git.

REPO_FULL_NAME="${1:-UTAHOGA/HUNT-PLANNER}"
TARGET_PATH="${2:-data/ingestion/utah/2024}"
BRANCH="${3:-ingest/utah-2024-hunt-data}"
BASE_BRANCH="${4:-main}"
COMMIT_MSG="${5:-Add 2024 Utah hunt prediction ingestion data}"

WORKDIR="$(mktemp -d)"
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/data"

if [[ ! -d "$DATA_DIR" ]]; then
  echo "ERROR: data directory not found at $DATA_DIR" >&2
  exit 1
fi

if command -v gh >/dev/null 2>&1; then
  gh repo clone "$REPO_FULL_NAME" "$WORKDIR/repo"
else
  git clone "https://github.com/${REPO_FULL_NAME}.git" "$WORKDIR/repo"
fi

cd "$WORKDIR/repo"
git fetch origin "$BASE_BRANCH"
git checkout "$BASE_BRANCH"
git pull --ff-only origin "$BASE_BRANCH"

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git checkout "$BRANCH"
else
  git checkout -b "$BRANCH"
fi

mkdir -p "$TARGET_PATH"
rsync -a --delete "$DATA_DIR/" "$TARGET_PATH/"
cp "$SCRIPT_DIR/engine_payload_manifest.json" "$TARGET_PATH/engine_payload_manifest.json"

# Preserve the compact ZIP one level above the data payload if desired.
mkdir -p "$(dirname "$TARGET_PATH")"
cp "$SCRIPT_DIR/hunt_prediction_ingestion_2024.zip" "$(dirname "$TARGET_PATH")/hunt_prediction_ingestion_2024.zip"

git add "$TARGET_PATH" "$(dirname "$TARGET_PATH")/hunt_prediction_ingestion_2024.zip"

if git diff --cached --quiet; then
  echo "No changes to commit. Repository is already in sync."
  exit 0
fi

git commit -m "$COMMIT_MSG"
git push -u origin "$BRANCH"

echo "Sync complete. Branch pushed: $BRANCH"
echo "Open a pull request with: gh pr create --fill --base $BASE_BRANCH --head $BRANCH"
