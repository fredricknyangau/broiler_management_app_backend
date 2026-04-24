#!/bin/bash
##############################################################################
# Pre-commit Testing Script - Backend
#
# This script runs backend (Python/FastAPI) tests before committing.
# Runs only in the backend repository context.
#
##############################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Functions
print_header() {
  echo ""
  echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║  $1${NC}"
  echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
}

print_section() {
  echo -e "${CYAN}► $1${NC}"
}

run_with_timing() {
  local cmd="$1"
  local desc="$2"
  local start_time=$(date +%s)

  echo -e "${YELLOW}  Running: ${desc}${NC}"

  if eval "$cmd" 2>&1; then
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    echo -e "${GREEN}  ✅ ${desc} (${duration}s)${NC}"
    return 0
  else
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    echo -e "${RED}  ❌ ${desc} (${duration}s)${NC}"
    return 1
  fi
}

# Main execution
main() {
  print_header "Backend Pre-commit Tests"

  local total_start=$(date +%s)
  local failed_tests=()

  print_section "Python/FastAPI Tests"

  # Check if Docker is running
  if ! docker info >/dev/null 2>&1; then
    echo -e "${YELLOW}  ⚠️  Docker is not running${NC}"
    echo -e "${YELLOW}  To enable tests, start Docker and run: make up${NC}"
  else
    # Run pytest tests
    if ! run_with_timing "make test" "Pytest tests"; then
      failed_tests+=("tests")
    fi

    # Run migration check
    if ! run_with_timing "make migrate-check" "Database migration check"; then
      failed_tests+=("migrations")
    fi

    # Run linting
    if ! run_with_timing "make lint" "Code linting"; then
      failed_tests+=("lint")
    fi
  fi

  # Summary
  local total_end=$(date +%s)
  local total_duration=$((total_end - total_start))

  print_header "Results"

  if [ ${#failed_tests[@]} -eq 0 ]; then
    echo -e "${GREEN}🎉 All backend tests passed! (${total_duration}s)${NC}"
    echo ""
    exit 0
  else
    echo -e "${RED}❌ Tests failed: ${failed_tests[*]} (${total_duration}s)${NC}"
    echo ""
    echo -e "${YELLOW}To skip: git commit --no-verify${NC}"
    echo ""
    exit 1
  fi
}

main "$@"