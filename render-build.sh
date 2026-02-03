#!/usr/bin/env bash
# Render build script - Python backend only

set -e

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Build complete ==="
