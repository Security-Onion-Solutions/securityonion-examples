#!/bin/bash

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

# Parse command line arguments
SPECIFIC_TEST=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --test)
      SPECIFIC_TEST="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: $0 [--test test_path::test_name]"
      exit 1
      ;;
  esac
done

# Main script execution
echo -e "${GREEN}Running Shallot Backend tests in Docker with coverage...${NC}"
check_docker

# Build the test container with 50% coverage requirement for local testing
echo -e "${YELLOW}Building Docker test container with Python 3.13...${NC}"
docker build -t shallot-backend-tests -f Dockerfile.test \
    --target test \
    --build-arg PYTHON_VERSION=3.13 \
    --build-arg COVERAGE_THRESHOLD=50 .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Successfully built test container!${NC}"
    
    # Create a directory for the coverage reports
    mkdir -p coverage
    
    if [ -n "$SPECIFIC_TEST" ]; then
        echo -e "${YELLOW}Running specific test: $SPECIFIC_TEST ${NC}"
        # Create and run container with specific test
        docker run --rm shallot-backend-tests poetry run pytest $SPECIFIC_TEST -v
    else
        echo -e "${YELLOW}Extracting test results and coverage data...${NC}"
        # Create a container to extract coverage data from
        CONTAINER_ID=$(docker create shallot-backend-tests)
        
        # Copy the coverage reports from the container
        docker cp $CONTAINER_ID:/app/coverage/htmlcov ./coverage/
        docker cp $CONTAINER_ID:/app/coverage/.coverage ./coverage/
        
        # Clean up
        docker rm $CONTAINER_ID
        
        echo -e "${GREEN}Tests completed!${NC}"
        echo -e "${YELLOW}Coverage report is available in ./coverage/htmlcov/index.html${NC}"
        echo -e "${YELLOW}Coverage threshold is set to 50% to allow for temporary development flexibility${NC}"
    fi
else
    echo -e "${RED}Failed to build test container${NC}"
    exit 1
fi