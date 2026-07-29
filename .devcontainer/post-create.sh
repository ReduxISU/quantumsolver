#!/usr/bin/env bash
set -euo pipefail

# .venv is a container-local volume so it never collides with the host venv; make it writable.
sudo chown "$(id -u):$(id -g)" .venv

# uv is provided by the rbs feature; it installs system-wide to /usr/local/bin.
uv sync --all-groups
