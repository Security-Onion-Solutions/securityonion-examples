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

# Change to script directory
cd "$(dirname "$0")"

echo -e "${GREEN}Starting Vidalia setup...${NC}"

# Check for required packages
if ! command -v python3.13 &> /dev/null; then
    echo -e "${RED}Error: python3.13 is not installed${NC}"
    echo -e "${YELLOW}Please install python3.13${NC}"
    exit 1
fi

# Check for python3.13-venv
if ! dpkg -l | grep -q python3.13-venv; then
    echo -e "${RED}Error: python3.13-venv is not installed${NC}"
    echo -e "${YELLOW}Please install it with: sudo apt install python3.13-venv${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    if ! python3.13 -m venv venv; then
        echo -e "${RED}Error: Failed to create virtual environment${NC}"
        exit 1
    fi
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
if [ ! -f "venv/bin/activate" ]; then
    echo -e "${RED}Error: Virtual environment activation script not found${NC}"
    echo -e "${YELLOW}Trying to recreate virtual environment...${NC}"
    rm -rf venv
    if ! python3.13 -m venv venv; then
        echo -e "${RED}Error: Failed to recreate virtual environment${NC}"
        exit 1
    fi
fi

if ! source venv/bin/activate 2>/dev/null; then
    echo -e "${RED}Error: Failed to activate virtual environment${NC}"
    exit 1
fi

# Verify virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}Error: Virtual environment not properly activated${NC}"
    exit 1
fi

# Install/upgrade pip within virtual environment
echo -e "${YELLOW}Upgrading pip...${NC}"
if ! ./venv/bin/python -m pip install --upgrade pip; then
    echo -e "${RED}Error: Failed to upgrade pip${NC}"
    echo -e "${YELLOW}This might be due to system restrictions. Continuing anyway...${NC}"
fi

# Install requirements
echo -e "${YELLOW}Installing requirements...${NC}"
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: requirements.txt not found${NC}"
    exit 1
fi

if ! ./venv/bin/python -m pip install -r requirements.txt; then
    echo -e "${RED}Error: Failed to install requirements${NC}"
    exit 1
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env file template...${NC}"
    # Generate a random secret key
    RANDOM_SECRET=$(python3.13 -c 'import secrets; print(secrets.token_hex(24))')
    
    cat > .env << EOL
# Flask configuration
# A secure random key is generated for you, but you can change it if needed
SECRET_KEY=${RANDOM_SECRET}

# Security Onion API configuration
# The URL of your Security Onion instance (include port)
SO_API_URL=https://your-so-manager:443

# Security Onion API credentials
# Get these from your Security Onion instance
# DO NOT commit this file to version control!
SO_CLIENT_ID=your_client_id_here
SO_CLIENT_SECRET=your_client_secret_here
EOL
    echo -e "${GREEN}Created .env file. Please update with your Security Onion API credentials.${NC}"
fi

# Add Flask development environment variables
export FLASK_APP=src/app.py
export FLASK_ENV=development
export FLASK_DEBUG=1

# Check if we should run tests
if [ "$1" = "test" ]; then
    echo -e "${GREEN}Running tests...${NC}"
    # Ensure src module is in Python path and run tests
    PYTHONPATH=$PYTHONPATH:. ./venv/bin/python -m pytest
else
    echo -e "${GREEN}Starting Flask development server...${NC}"
    # Ensure src module is in Python path and start Flask with auto-reload
    PYTHONPATH=$PYTHONPATH:. ./venv/bin/python -m flask run --reload
fi
