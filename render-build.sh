#!/usr/bin/env bash
# Render build script - Python only (frontend is in root index.html)

set -e

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Build complete ==="
