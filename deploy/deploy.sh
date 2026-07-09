#!/usr/bin/env bash
set -euo pipefail

REF="${1:-main}"
DEPLOY_DIR="/home/redux/quantumsolver"
SERVICE="quantumsolver.service"

cd "$DEPLOY_DIR"

echo "==> Fetching..."
git fetch --all --tags --prune

echo "==> Resetting to ${REF}..."
# Try as a remote branch first; fall back to tag or commit hash.
git reset --hard "origin/${REF}" 2>/dev/null || git reset --hard "${REF}"

echo "==> Syncing dependencies..."
# Creates/updates .venv from uv.lock (runtime deps only) and installs the
# quantumsolver package. Requires uv on the deploy user's PATH.
uv sync --frozen --no-dev

echo "==> Restarting service..."
sudo /usr/bin/systemctl restart "$SERVICE"

echo "==> Done."
