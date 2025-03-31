#!/bin/bash

# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

# Check if certificates exist
if [ ! -f "shallotbot/certs/certificate.crt" ] || [ ! -f "shallotbot/certs/private.key" ]; then
    echo "Error: SSL certificates not found in shallotbot/certs/"
    echo "Please run ./generate-environment.sh first to set up the environment"
    exit 1
fi

# Check if .env exists
if [ ! -f "shallotbot/.env" ]; then
    echo "Error: .env file not found in shallotbot/"
    echo "Please run ./generate-environment.sh first to set up the environment"
    exit 1
fi

# Build Docker image
echo "Building Docker image..."
docker build \
    --build-arg NGINX_UID=$(id -u) \
    --build-arg NGINX_GID=$(id -g) \
    -t shallot-bot .

# Check if build was successful
if [ $? -ne 0 ]; then
    echo "Error: Docker build failed"
    exit 1
fi

# Ask for port configuration
read -p "Enter the port number for HTTPS (default: 443): " port
port=${port:-443}

# Confirm starting the container
read -p "Do you want to start the container now? (y/n): " start_container

if [ "$start_container" = "y" ] || [ "$start_container" = "Y" ]; then
    # Check for and remove existing container
    if docker ps -a | grep -q shallot-bot; then
        echo "Removing existing container..."
        docker rm -f shallot-bot
    fi

    # Get current user's UID and GID
    USER_ID=$(id -u)
    GROUP_ID=$(id -g)

    # Ensure required directories exist with correct permissions
    mkdir -p "$(pwd)/shallotbot/data" "$(pwd)/shallotbot/certs" \
            "$(pwd)/shallotbot/logs/nginx" "$(pwd)/shallotbot/logs/app"
    
    # Create log files if they don't exist
    touch "$(pwd)/shallotbot/logs/nginx/access.log" "$(pwd)/shallotbot/logs/nginx/error.log" \
          "$(pwd)/shallotbot/logs/app/backend.log" "$(pwd)/shallotbot/logs/app/docker.log"
    
    # Set directory permissions to be writable by the container
    find "$(pwd)/shallotbot/logs" -type d -exec chmod 777 {} \;
    # Set file permissions to be writable by the container
    find "$(pwd)/shallotbot/logs" -type f -exec chmod 666 {} \;

    echo "Starting container with port $port as user $USER_ID:$GROUP_ID..."
    docker run -d \
        --name shallot-bot \
        -p "0.0.0.0:$port:8443" \
        -v "$(pwd)/shallotbot/data/:/app/data/" \
        -v "$(pwd)/shallotbot/certs/:/opt/shallot/certs/" \
        -v "$(pwd)/shallotbot/.env:/opt/shallot/.env" \
        -v "$(pwd)/shallotbot/logs/:/app/logs/" \
        -e NGINX_UID=$USER_ID \
        -e NGINX_GID=$GROUP_ID \
        shallot-bot

    if [ $? -eq 0 ]; then
        echo "Container started successfully!"
        echo "The application is now available at https://localhost:$port"
    else
        echo "Error: Failed to start container"
        exit 1
    fi
else
    echo "Container not started. You can start it later with:"
    echo "docker run -d \\"
    echo "    --name shallot-bot \\"
    echo "    -p 0.0.0.0:$port:8443 \\"
    echo "    -v \"\$(pwd)/shallotbot/data/:/app/data/\" \\"
    echo "    -v \"\$(pwd)/shallotbot/certs/:/opt/shallot/certs/\" \\"
    echo "    -v \"\$(pwd)/shallotbot/.env:/opt/shallot/.env\" \\"
    echo "    -v \"\$(pwd)/shallotbot/logs/:/app/logs/\" \\"
    echo "    -e NGINX_UID=\$(id -u) \\"
    echo "    -e NGINX_GID=\$(id -g) \\"
    echo "    shallot-bot"
fi
