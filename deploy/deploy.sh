#!/usr/bin/env bash
set -euo pipefail

REF="${1:-main}"
DEPLOY_DIR="/home/redux/quantumsolver"
VENV="$DEPLOY_DIR/.venv"
SERVICE="quantumsolver.service"

cd "$DEPLOY_DIR"

echo "==> Fetching..."
git fetch --all --tags --prune

echo "==> Resetting to ${REF}..."
# Try as a remote branch first; fall back to tag or commit hash.
git reset --hard "origin/${REF}" 2>/dev/null || git reset --hard "${REF}"

echo "==> Syncing dependencies..."
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
fi
if ! "$VENV/bin/pip-sync" --version &>/dev/null; then
    # pip-sync not yet installed (first deploy); bootstrap it.
    "$VENV/bin/pip" install --quiet pip-tools
fi
"$VENV/bin/pip-sync" requirements.txt

echo "==> Restarting service..."
sudo /usr/bin/systemctl restart "$SERVICE"

echo "==> Done."
