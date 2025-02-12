#!/bin/bash

# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

# Exit on error
set -e

# Function to handle errors
handle_error() {
    echo "Error: $1"
    exit 1
}

# Ensure python3-venv is installed
if ! command -v python3 &> /dev/null; then
    handle_error "Python 3 is not installed. Please install Python 3 first."
fi

# Remove existing venv if it exists
if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

# Create fresh virtual environment
echo "Creating virtual environment..."
python3 -m venv venv || handle_error "Failed to create virtual environment. Try installing python3-venv package if needed."

# Ensure virtual environment was created
if [ ! -f "venv/bin/activate" ]; then
    handle_error "Virtual environment creation failed"
fi

# Activate virtual environment
echo "Activating virtual environment..."
. venv/bin/activate || handle_error "Failed to activate virtual environment"

# Verify we're in the virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    handle_error "Not in virtual environment"
fi

# Install requirements using the virtual environment's pip
echo "Installing requirements..."
venv/bin/pip install -r requirements.txt || handle_error "Failed to install requirements"

# Run tests with verbose output
echo "Running tests..."
python -m pytest -v || handle_error "Tests failed"

# Deactivate virtual environment
deactivate

echo "Test run completed successfully!"
