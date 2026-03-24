#!/usr/bin/env bash
# Render build script — installs Python deps and builds the React frontend

set -e

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Building React frontend ==="
cd app
npm install
npm run build
cd ..

echo "=== Build complete ==="
echo "React app built into app/dist/"
ls -la app/dist/ 2>/dev/null || echo "Warning: app/dist/ not found"
