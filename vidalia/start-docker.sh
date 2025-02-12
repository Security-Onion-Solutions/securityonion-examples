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

# Function to check if a port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 1
    fi
    return 0
}

# Function to get port number
get_port() {
    local default_port=5000
    local port

    while true; do
        read -p "Enter port for Vidalia container [$default_port]: " port
        port=${port:-$default_port}

        if ! [[ "$port" =~ ^[0-9]+$ ]] || [ "$port" -lt 1024 ] || [ "$port" -gt 65535 ]; then
            echo -e "${RED}Invalid port number. Please enter a number between 1024 and 65535${NC}"
            continue
        fi

        if ! check_port "$port"; then
            echo -e "${RED}Port $port is already in use. Please choose another port${NC}"
            continue
        fi

        break
    done

    echo "$port"
}

# Function to check and update Security Onion configuration
setup_config() {
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}Security Onion configuration not found. Setting up...${NC}"
        
        # Generate random secret key
        RANDOM_SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(24))')
        
        # Get SO API URL
        read -p "Enter Security Onion API URL [https://SOMANAGER:443]: " SO_API_URL
        SO_API_URL=${SO_API_URL:-https://SOMANAGER:443}
        
        # Get SO Client ID
        read -p "Enter Security Onion Client ID: " SO_CLIENT_ID
        while [ -z "$SO_CLIENT_ID" ]; do
            echo -e "${RED}Client ID cannot be empty${NC}"
            read -p "Enter Security Onion Client ID: " SO_CLIENT_ID
        done
        
        # Get SO Client Secret
        read -s -p "Enter Security Onion Client Secret: " SO_CLIENT_SECRET
        echo
        while [ -z "$SO_CLIENT_SECRET" ]; do
            echo -e "${RED}Client Secret cannot be empty${NC}"
            read -s -p "Enter Security Onion Client Secret: " SO_CLIENT_SECRET
            echo
        done
        
        # Create .env file
        cat > .env << EOL
# Flask configuration
SECRET_KEY=${RANDOM_SECRET}

# Security Onion API configuration
SO_API_URL=${SO_API_URL}
SO_CLIENT_ID=${SO_CLIENT_ID}
SO_CLIENT_SECRET=${SO_CLIENT_SECRET}
EOL
        
        echo -e "${GREEN}Security Onion configuration saved to .env file${NC}"
    fi
}

# Function to start the container
start() {
    setup_config
    export PORT=$(get_port)
    
    # Build and start the container
    echo -e "${GREEN}Building and starting Vidalia container on port $PORT...${NC}"
    docker build -t vidalia -f docker/Dockerfile .
    
    if [ $? -eq 0 ]; then
        docker stop vidalia 2>/dev/null || true
        docker rm vidalia 2>/dev/null || true
        
        docker run -d \
            --name vidalia \
            -p "${PORT}:5000" \
            -v "$(pwd)/logs:/app/logs" \
            --env-file .env \
            --add-host=host.docker.internal:host-gateway \
            -e PYTHONPATH=/app \
            -e FLASK_APP=src/app.py \
            vidalia
            
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Container started successfully!${NC}"
            echo -e "Access Vidalia at http://localhost:$PORT"
        else
            echo -e "${RED}Failed to start container${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Failed to build container${NC}"
        exit 1
    fi
}

# Function to stop the container
stop() {
    echo -e "${YELLOW}Stopping Vidalia container...${NC}"
    docker stop vidalia
    docker rm vidalia
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Container stopped successfully${NC}"
    else
        echo -e "${RED}Failed to stop container${NC}"
        exit 1
    fi
}

# Function to show container logs
logs() {
    docker logs -f vidalia
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [command]"
    echo
    echo "Commands:"
    echo "  start    Start container (default if no command provided)"
    echo "  stop     Stop container"
    echo "  logs     View container logs"
    echo "  config   Update Security Onion configuration"
}

# Main script
check_docker

# Use 'start' as default command if none provided
COMMAND=${1:-start}

case "$COMMAND" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    logs)
        logs
        ;;
    config)
        setup_config
        ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        show_usage
        exit 1
        ;;
esac
