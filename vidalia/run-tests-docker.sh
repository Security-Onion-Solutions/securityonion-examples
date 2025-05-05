#!/bin/bash

# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: docker is not installed${NC}"
        echo -e "${YELLOW}Please install Docker first${NC}"
        exit 1
    fi
}

# Main script execution
echo -e "${GREEN}Running Vidalia tests in Docker with coverage...${NC}"
check_docker

# Build and run the test container
docker build -t vidalia-tests -f docker/Dockerfile.test .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Successfully built test container, running tests...${NC}"
    
    # Run tests in container
    docker run --rm vidalia-tests
    
    TEST_RESULT=$?
    if [ $TEST_RESULT -eq 0 ]; then
        echo -e "${GREEN}All tests passed successfully!${NC}"
    else
        echo -e "${RED}Tests failed with exit code ${TEST_RESULT}${NC}"
        exit $TEST_RESULT
    fi
else
    echo -e "${RED}Failed to build test container${NC}"
    exit 1
fi