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

echo "=== Starting CLI server for page generation ==="
# Start CLI server in background
PORT=3099 node dist/cli.js serve &
CLI_PID=$!
echo "CLI PID: $CLI_PID"

# Wait for server to be ready (longer wait, better detection)
echo "Waiting for CLI server to start..."
MAX_WAIT=60
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
  if curl -s http://localhost:3099/ > /dev/null 2>&1; then
    echo "CLI server ready after ${WAIT_COUNT}s!"
    break
  fi
  WAIT_COUNT=$((WAIT_COUNT + 1))
  sleep 1
  if [ $((WAIT_COUNT % 10)) -eq 0 ]; then
    echo "  Still waiting... ${WAIT_COUNT}s"
  fi
done

if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
  echo "ERROR: CLI server failed to start after ${MAX_WAIT}s"
  echo "Checking if process is running..."
  ps aux | grep node || true
  exit 1
fi

# Verify server is responding
echo "Verifying CLI server responds..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3099/companies)
if [ "$HTTP_CODE" != "200" ]; then
  echo "ERROR: CLI server not responding correctly. HTTP code: $HTTP_CODE"
  exit 1
fi
echo "CLI server verified (HTTP $HTTP_CODE)"

# Create static pages directories
echo "=== Creating static pages directories ==="
mkdir -p ../static/pages/company

# Fetch main pages with verification
echo "=== Generating main pages ==="

fetch_page() {
  local URL=$1
  local OUTPUT=$2
  local NAME=$3

  echo "Fetching $NAME..."
  HTTP_CODE=$(curl -s -o "$OUTPUT" -w "%{http_code}" "$URL")

  if [ "$HTTP_CODE" != "200" ]; then
    echo "  ERROR: Failed to fetch $NAME (HTTP $HTTP_CODE)"
    return 1
  fi

  SIZE=$(wc -c < "$OUTPUT" | tr -d ' ')
  if [ "$SIZE" -lt 100 ]; then
    echo "  ERROR: $NAME is too small ($SIZE bytes)"
    return 1
  fi

  echo "  OK: $NAME ($SIZE bytes)"
  return 0
}

fetch_page "http://localhost:3099/companies" "../static/pages/companies.html" "/companies"
fetch_page "http://localhost:3099/targets" "../static/pages/targets.html" "/targets"
fetch_page "http://localhost:3099/kols" "../static/pages/kols.html" "/kols"
fetch_page "http://localhost:3099/about" "../static/pages/about.html" "/about"
fetch_page "http://localhost:3099/research" "../static/pages/research.html" "/research"

# Extract all company tickers and generate detail pages
echo "=== Generating company detail pages ==="
TICKERS=$(curl -s http://localhost:3099/companies | grep -o '/api/company/[A-Z]*/html' | sed 's|/api/company/||g' | sed 's|/html||g' | sort -u)
TICKER_COUNT=$(echo "$TICKERS" | wc -l | tr -d ' ')
echo "Found $TICKER_COUNT company tickers"

SUCCESS_COUNT=0
FAIL_COUNT=0

for TICKER in $TICKERS; do
  HTTP_CODE=$(curl -s -o "../static/pages/company/${TICKER}.html" -w "%{http_code}" "http://localhost:3099/api/company/${TICKER}/html" 2>/dev/null)
  if [ "$HTTP_CODE" = "200" ]; then
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
  else
    echo "  Failed: $TICKER (HTTP $HTTP_CODE)"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
done

echo "Company pages: $SUCCESS_COUNT succeeded, $FAIL_COUNT failed"

# Kill CLI server
echo "=== Stopping CLI server ==="
kill $CLI_PID 2>/dev/null || true
sleep 2

cd ..

# Final verification
echo "=== Final verification ==="
echo "Main pages:"
for PAGE in companies.html targets.html kols.html about.html research.html; do
  if [ -f "static/pages/$PAGE" ]; then
    SIZE=$(wc -c < "static/pages/$PAGE" | tr -d ' ')
    echo "  ✓ $PAGE ($SIZE bytes)"
  else
    echo "  ✗ $PAGE MISSING"
  fi
done

echo ""
COMPANY_COUNT=$(ls static/pages/company/*.html 2>/dev/null | wc -l | tr -d ' ')
echo "Company detail pages: $COMPANY_COUNT generated"

if [ "$COMPANY_COUNT" -lt 10 ]; then
  echo "WARNING: Very few company pages generated. Build may have issues."
fi

echo ""
echo "=== Build complete ==="
