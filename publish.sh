#!/usr/bin/env bash
set -e  # Exit immediately if any command returns non‐zero

echo "••• Upgrading build & twine…"
pip install --upgrade build twine

echo "••• Cleaning old distributions…"
rm -rf dist/ build/ *.egg-info

echo "••• Building new package…"
python -m build

echo "••• Uploading to PyPI…"
twine upload dist/*

echo "✅ Done!"
