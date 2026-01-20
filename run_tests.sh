#!/bin/bash
# =============================================================================
# BHNBot Test Runner Script
# =============================================================================
# 
# Usage:
#   ./run_tests.sh              # Run all tests
#   ./run_tests.sh seasonal     # Run only seasonal tests
#   ./run_tests.sh -v           # Run with verbose output
#   ./run_tests.sh --cov        # Run with coverage report
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Virtual environment
VENV_PATH=".venv"
PYTHON="$VENV_PATH/bin/python3"
PIP="$VENV_PATH/bin/pip"
PYTEST="$VENV_PATH/bin/pytest"

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo -e "${BLUE}=============================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}=============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# =============================================================================
# Check Prerequisites
# =============================================================================

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check if venv exists
    if [ ! -d "$VENV_PATH" ]; then
        print_error "Virtual environment not found at $VENV_PATH"
        echo "  Run: python3 -m venv .venv"
        exit 1
    fi
    print_success "Virtual environment found"
    
    # Check if pytest is installed
    if [ ! -f "$PYTEST" ]; then
        print_warning "pytest not installed. Installing test dependencies..."
        $PIP install -r requirements-dev.txt
    fi
    print_success "pytest is available"
    
    # Check if requirements-dev.txt exists
    if [ ! -f "requirements-dev.txt" ]; then
        print_warning "requirements-dev.txt not found"
    else
        print_success "requirements-dev.txt found"
    fi
    
    echo ""
}

# =============================================================================
# Run Tests
# =============================================================================

run_tests() {
    local test_path="${1:-tests/}"
    local extra_args="${@:2}"
    
    print_header "Running Tests: $test_path"
    
    # Default pytest arguments
    local pytest_args="-v --tb=short"
    
    # Add coverage if requested
    if [[ "$extra_args" == *"--cov"* ]]; then
        pytest_args="$pytest_args --cov=cogs --cov-report=html --cov-report=term-missing"
    fi
    
    # Run pytest
    echo "Command: $PYTEST $test_path $pytest_args $extra_args"
    echo ""
    
    if $PYTEST $test_path $pytest_args $extra_args; then
        echo ""
        print_success "All tests passed!"
    else
        echo ""
        print_error "Some tests failed!"
        exit 1
    fi
}

# =============================================================================
# Test Categories
# =============================================================================

run_unit_tests() {
    print_header "Running Unit Tests"
    $PYTEST tests/ -m "unit" -v
}

run_integration_tests() {
    print_header "Running Integration Tests"
    $PYTEST tests/ -m "integration" -v
}

run_seasonal_tests() {
    print_header "Running Seasonal Event Tests"
    $PYTEST tests/seasonal/ -v
}

run_json_validation() {
    print_header "Running JSON Validation Tests"
    $PYTEST tests/seasonal/test_json_configs.py -v
}

# =============================================================================
# Generate Coverage Report
# =============================================================================

generate_coverage() {
    print_header "Generating Coverage Report"
    
    $PYTEST tests/ \
        --cov=cogs \
        --cov-report=html \
        --cov-report=term-missing \
        --cov-fail-under=30
    
    echo ""
    print_success "Coverage report generated at htmlcov/index.html"
}

# =============================================================================
# Main
# =============================================================================

main() {
    check_prerequisites
    
    case "${1:-all}" in
        "all")
            run_tests "tests/"
            ;;
        "seasonal")
            run_seasonal_tests
            ;;
        "unit")
            run_unit_tests
            ;;
        "integration")
            run_integration_tests
            ;;
        "json")
            run_json_validation
            ;;
        "coverage")
            generate_coverage
            ;;
        *)
            # Pass all arguments to pytest
            run_tests "$@"
            ;;
    esac
}

# Run main with all arguments
main "$@"
