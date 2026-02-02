#!/usr/bin/env bash
# Render build script - Python backend + pre-generated Node pages

set -e

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Installing Node CLI dependencies ==="
cd cli
npm install

echo "=== Building CLI ==="
npm run build

echo "=== Generating static pages from CLI ==="
# Start CLI server in background
PORT=3099 npm start &
CLI_PID=$!

# Wait for server to be ready
echo "Waiting for CLI server to start..."
for i in {1..30}; do
  if curl -s http://localhost:3099/health > /dev/null 2>&1 || curl -s http://localhost:3099/ > /dev/null 2>&1; then
    echo "CLI server ready!"
    break
  fi
  sleep 1
done

# Create static pages directory
mkdir -p ../static/pages

# Fetch and save dynamic pages
echo "Fetching /companies..."
curl -s http://localhost:3099/companies > ../static/pages/companies.html || echo "Failed to fetch /companies"

echo "Fetching /targets..."
curl -s http://localhost:3099/targets > ../static/pages/targets.html || echo "Failed to fetch /targets"

echo "Fetching /kols..."
curl -s http://localhost:3099/kols > ../static/pages/kols.html || echo "Failed to fetch /kols"

echo "Fetching /about..."
curl -s http://localhost:3099/about > ../static/pages/about.html || echo "Failed to fetch /about"

echo "Fetching /research..."
curl -s http://localhost:3099/research > ../static/pages/research.html || echo "Failed to fetch /research"

# Kill CLI server
kill $CLI_PID 2>/dev/null || true

cd ..

echo "=== Verifying generated pages ==="
ls -la static/pages/

echo "=== Build complete ==="
