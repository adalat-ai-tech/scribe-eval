#!/usr/bin/env bash
# Build the demo site's generated artifacts in-place (local development).
# CI (.github/workflows/deploy-pages.yml) performs the same three steps
# into an isolated _site/ directory.
#
# Usage: ./scripts/build_demo_site.sh
# Then:  python -m http.server 8000 -d site

set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Building wheel =="
uv build --wheel

echo "== Staging wheel + manifest =="
mkdir -p site/wheels
rm -f site/wheels/*.whl
cp dist/scribe_eval-*.whl site/wheels/
WHEEL=$(basename site/wheels/scribe_eval-*.whl)
printf '{"wheel": "%s"}\n' "$WHEEL" > site/wheels/manifest.json
echo "   $WHEEL"

echo "== Baking showcase results =="
uv run python scripts/generate_showcase_data.py

echo "== Done. Serve with: python -m http.server 8000 -d site =="
