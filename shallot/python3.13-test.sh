#!/bin/bash
set -e

# Script to build and test the Docker container with Python 3.13

# Step 1: Generate environment if needed
if [ ! -f ./shallotbot/.env ]; then
  echo "Generating environment file..."
  ./generate-environment.sh
fi

# Step 2: Build the Docker container 
echo "Building Docker container with Python 3.13..."
docker build --build-arg NGINX_UID=$(id -u) --build-arg NGINX_GID=$(id -g) -t shallot-bot-py3.13 .

# Step 3: Run tests in the container
echo "Running container for testing..."
docker run --rm -it -p 8443:8443 \
  -v $(pwd)/shallotbot/data:/app/data \
  -v $(pwd)/shallotbot/logs:/app/logs \
  -v $(pwd)/shallotbot/certs:/etc/nginx/ssl \
  -v $(pwd)/shallotbot/.env:/opt/shallot/.env \
  shallot-bot-py3.13

echo "Test completed. Container exited with status $?"