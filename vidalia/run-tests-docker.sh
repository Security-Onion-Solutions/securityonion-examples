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

# Build the test container with 100% coverage requirement
docker build -t vidalia-tests -f docker/Dockerfile.test \
    --target test \
    --build-arg PYTHON_VERSION=3.13 \
    --build-arg COVERAGE_THRESHOLD=100 .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Successfully built test container with tests and coverage...${NC}"
    
    # Create a directory for the coverage reports
    mkdir -p coverage
    
    # Run tests and extract coverage data
    CONTAINER_ID=$(docker create vidalia-tests)
    
    # Copy the coverage reports from the container
    docker cp $CONTAINER_ID:/app/coverage/htmlcov ./coverage/
    docker cp $CONTAINER_ID:/app/coverage/.coverage ./coverage/
    
    # Clean up
    docker rm $CONTAINER_ID
    
    echo -e "${GREEN}All tests passed with 100% coverage!${NC}"
    echo -e "${YELLOW}Coverage report is available in ./coverage/htmlcov/index.html${NC}"
else
    echo -e "${RED}Failed to build test container${NC}"
    exit 1
fi