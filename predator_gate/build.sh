#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="${PROJECT_ROOT}/build"

echo "================================================"
echo "  SOVEREIGN BURNER - BUILD"
echo "================================================"

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "-> Configuring CMake..."
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

echo "-> Building..."
make -j$(nproc)

echo ""
echo "-> Verifying shared library..."
if [ -f "libpredator_gate.so" ]; then
    ls -lh libpredator_gate.so
    echo ""
    echo "Exported symbols:"
    nm -D --defined-only libpredator_gate.so | grep burner_ || echo "none found"
else
    echo "libpredator_gate.so not found - check build output above"
fi

echo ""
echo "================================================"
echo "  BUILD COMPLETE"
echo "================================================"
