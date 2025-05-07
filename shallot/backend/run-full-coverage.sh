#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Create coverage directory if it doesn't exist
mkdir -p coverage

echo -e "${GREEN}Running full test suite with coverage...${NC}"

# Run tests with complete coverage reporting
poetry run pytest tests/test_*_service*.py tests/test_*_model*.py tests/test_*_complete*.py -v \
    --cov=src/app \
    --cov-report=term \
    --cov-report=html:coverage/htmlcov \
    --cov-report=json:coverage/coverage.json \
    "$@"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    echo -e "${YELLOW}Coverage report is available in ./coverage/htmlcov/index.html${NC}"
else
    echo -e "${RED}Some tests failed. Please check the output above.${NC}"
    exit 1
fi