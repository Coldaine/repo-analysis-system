#!/bin/bash
# Comprehensive test runner script with different test modes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
MODE="all"
VERBOSE=0
COVERAGE=0

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=1
            shift
            ;;
        --coverage|-c)
            COVERAGE=1
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --mode MODE       Test mode: unit, integration, e2e, live, all (default: all)"
            echo "  --verbose, -v     Verbose output"
            echo "  --coverage, -c    Generate coverage report"
            echo "  --help, -h        Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}Repository Analysis System - Test Runner${NC}"
echo "=========================================="
echo "Mode: $MODE"
echo ""

# Setup Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Build pytest command
PYTEST_CMD="pytest tests/"

if [ $VERBOSE -eq 1 ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ $COVERAGE -eq 1 ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src --cov-report=html --cov-report=term-missing"
fi

# Run tests based on mode
case $MODE in
    unit)
        echo -e "${YELLOW}Running unit tests...${NC}"
        $PYTEST_CMD -m "unit"
        ;;
    integration)
        echo -e "${YELLOW}Running integration tests...${NC}"
        $PYTEST_CMD -m "integration and not live"
        ;;
    e2e)
        echo -e "${YELLOW}Running end-to-end tests...${NC}"
        $PYTEST_CMD -m "e2e and not live"
        ;;
    live)
        if [ -z "$GITHUB_TOKEN" ]; then
            echo -e "${RED}Error: GITHUB_TOKEN environment variable not set${NC}"
            echo "Live tests require GitHub API access"
            exit 1
        fi
        echo -e "${YELLOW}Running live API tests...${NC}"
        $PYTEST_CMD -m "live"
        ;;
    fast)
        echo -e "${YELLOW}Running fast tests (unit + integration)...${NC}"
        $PYTEST_CMD -m "not live and not slow and not e2e"
        ;;
    all)
        echo -e "${YELLOW}Running all tests (excluding live tests)...${NC}"
        $PYTEST_CMD -m "not live"
        ;;
    full)
        if [ -z "$GITHUB_TOKEN" ]; then
            echo -e "${YELLOW}Warning: GITHUB_TOKEN not set, skipping live tests${NC}"
            $PYTEST_CMD -m "not live"
        else
            echo -e "${YELLOW}Running full test suite (including live tests)...${NC}"
            $PYTEST_CMD
        fi
        ;;
    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo "Valid modes: unit, integration, e2e, live, fast, all, full"
        exit 1
        ;;
esac

# Show coverage report location if generated
if [ $COVERAGE -eq 1 ]; then
    echo ""
    echo -e "${GREEN}Coverage report generated:${NC}"
    echo "  HTML: htmlcov/index.html"
fi

echo ""
echo -e "${GREEN}Tests completed!${NC}"
