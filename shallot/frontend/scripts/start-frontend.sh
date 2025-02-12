#!/bin/bash

# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

# Default configuration
DEV_SERVER_PORT=5173
WITH_CHECKS=false

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --with-checks) WITH_CHECKS=true ;;
        --port) DEV_SERVER_PORT="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Ensure we're in the frontend directory
cd "$(dirname "$0")/.." || exit 1

# Check if node_modules exists, if not install dependencies
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Run checks if requested
if [ "$WITH_CHECKS" = true ]; then
    echo "Running type check..."
    npm run type-check
    
    echo "Running linting..."
    npm run lint
    
    echo "Running tests..."
    npm run test:unit
fi

# Start the development server
echo "Starting development server on port $DEV_SERVER_PORT..."
npm run dev -- --port "$DEV_SERVER_PORT"
