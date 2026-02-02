#!/usr/bin/env bash
# Render build script - builds both Python and React

set -e

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Building React frontend ==="
cd app
npm install
npm run build
cd ..

echo "=== Build complete ==="
