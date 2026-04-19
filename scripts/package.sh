#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

rm -rf dist

uv run pytest

uv run gtp-cli convert 'tests/7和弦順階連奏.xml' \
  --force \
  --dry-run > /tmp/gtp-cli-e2e.applescript

osacompile -o /tmp/gtp-cli-e2e.scpt /tmp/gtp-cli-e2e.applescript

uv build

echo "Built packages:"
ls -lh dist
