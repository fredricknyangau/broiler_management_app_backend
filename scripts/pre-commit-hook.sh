#!/bin/bash
##############################################################################
# Pre-commit Git Hook for Backend
#
# This hook runs automatically before each commit to ensure code quality.
# It runs backend tests to prevent broken commits.
#
##############################################################################

# Run the pre-commit tests script
./scripts/pre-commit-tests.sh

# Exit with the same code as the test script
exit $?