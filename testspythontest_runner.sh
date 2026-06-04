# ═══════════════════════════════════════════════════════════════
#  tests/python/test_runner.sh
#  Run the full test suite with coverage report
# ═══════════════════════════════════════════════════════════════

#!/usr/bin/env bash
set -euo pipefail

CYAN='\033[96m'
GREEN='\033[92m'
RED='\033[91m'
BOLD='\033[1m'
RESET='\033[0m'

echo ""
echo -e "${CYAN}${BOLD}╔═══════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}${BOLD}║  AiZQuad Lab — Test Suite Runner         ║${RESET}"
echo -e "${CYAN}${BOLD}╚═══════════════════════════════════════════╝${RESET}"
echo ""

# Activate venv if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run Python tests
echo -e "${BOLD}Running Python tests...${RESET}"
python -m pytest tests/python/ \
    -v \
    --tb=short \
    --cov=. \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-fail-under=80 \
    -q

echo ""

# Run C++ tests if built
if [ -f "build/cpp/mesh_tests" ]; then
    echo -e "${BOLD}Running C++ tests...${RESET}"
    ./build/cpp/mesh_tests --gtest_color=yes
else
    echo -e "  ${CYAN}Skipping C++ tests (not built)${RESET}"
    echo -e "  Run: make cpp-build BUILD_TESTS=ON"
fi

echo ""
echo -e "${GREEN}${BOLD}╔═══════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}${BOLD}║  ALL TESTS PASSED                        ║${RESET}"
echo -e "${GREEN}${BOLD}╚═══════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  Coverage report: ${CYAN}htmlcov/index.html${RESET}"
echo ""
# ═══════════════════════════════════════════════════════════════
#  QUICK START
# ═══════════════════════════════════════════════════════════════

# Install deps
make install

# Run ALL tests
make test

# Run specific test file
pytest tests/python/test_lock.py -v

# Run specific test class
pytest tests/python/test_integrate.py::TestSessionManager -v

# Run specific test
pytest tests/python/test_integrate.py::TestLogicLock::test_tampered_code_detected -v

# Run with coverage
pytest tests/python/ --cov=. --cov-report=html

# Run C++ tests
make cpp-build BUILD_TESTS=ON
make cpp-test

# Run full shell suite
chmod +x tests/python/test_runner.sh
./tests/python/test_runner.sh
