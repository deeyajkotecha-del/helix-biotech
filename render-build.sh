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

# Create static pages directories
mkdir -p ../static/pages
mkdir -p ../static/pages/company

# Fetch main pages
echo "Fetching main pages..."
curl -s http://localhost:3099/companies > ../static/pages/companies.html || echo "Failed to fetch /companies"
curl -s http://localhost:3099/targets > ../static/pages/targets.html || echo "Failed to fetch /targets"
curl -s http://localhost:3099/kols > ../static/pages/kols.html || echo "Failed to fetch /kols"
curl -s http://localhost:3099/about > ../static/pages/about.html || echo "Failed to fetch /about"
curl -s http://localhost:3099/research > ../static/pages/research.html || echo "Failed to fetch /research"

# Extract all company tickers from companies page and generate detail pages
echo "Generating company detail pages..."
TICKERS=$(curl -s http://localhost:3099/companies | grep -o '/api/company/[A-Z]*/html' | sed 's|/api/company/||g' | sed 's|/html||g' | sort -u)

for TICKER in $TICKERS; do
  echo "  Fetching $TICKER..."
  curl -s "http://localhost:3099/api/company/${TICKER}/html" > "../static/pages/company/${TICKER}.html" 2>/dev/null || echo "    Failed: $TICKER"
done

# Kill CLI server
kill $CLI_PID 2>/dev/null || true

cd ..

echo "=== Verifying generated pages ==="
echo "Main pages:"
ls -la static/pages/*.html 2>/dev/null || echo "No main pages"
echo ""
echo "Company pages: $(ls static/pages/company/*.html 2>/dev/null | wc -l) generated"

echo "=== Build complete ==="
