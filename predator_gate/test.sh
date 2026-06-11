#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build"

echo "================================================"
echo "  SOVEREIGN BURNER - FULL TEST SUITE"
echo "================================================"

# Run C++ tests
echo ""
echo "-> Running C++ tests..."
cd "$BUILD_DIR"
./gate_test

# Run Python tests if bridge exists
if [ -f "python/test_bridge.py" ]; then
    echo ""
    echo "-> Running Python tests..."
    cd python
    python3 test_bridge.py
else
    echo ""
    echo "-> Python tests not yet present - skipping"
fi

echo ""
echo "================================================"
echo "  ALL TESTS COMPLETE"
echo "================================================"
