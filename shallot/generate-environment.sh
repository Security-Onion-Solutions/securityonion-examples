#!/bin/bash

# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.

# Function to generate a secure key using OpenSSL (hex format)
generate_hex_key() {
    openssl rand -hex 32
}

# Function to generate a Fernet key (url-safe base64 format)
generate_fernet_key() {
    openssl rand -base64 32 | tr '/+' '_-'
}

# Create shallotbot directory structure
echo "Creating directory structure..."
mkdir -p shallotbot/data
mkdir -p shallotbot/certs

# Generate self-signed SSL certificate
echo "Generating SSL certificates..."
openssl req -x509 \
    -newkey rsa:4096 \
    -keyout shallotbot/certs/private.key \
    -out shallotbot/certs/certificate.crt \
    -days 365 \
    -nodes \
    -subj "/C=US/ST=State/L=City/O=Security Onion Solutions/CN=localhost"

# Set proper permissions for SSL files
chmod 600 shallotbot/certs/private.key
chmod 644 shallotbot/certs/certificate.crt

# Create .env file
echo "Generating environment file..."
cat > shallotbot/.env << EOL
# Security Configuration
ENCRYPTION_KEY=$(generate_fernet_key)  # For database encryption (Fernet key)
SECRET_KEY=$(generate_hex_key)      # For JWT tokens
EOL

# Make the .env file readable only by the owner
chmod 600 shallotbot/.env

# Create empty database directory
touch shallotbot/data/.keep

echo "Setup completed successfully:"
echo "- Created shallotbot directory structure"
echo "- Generated SSL certificates in shallotbot/certs/"
echo "- Created environment file at shallotbot/.env"
echo "- Initialized data directory at shallotbot/data/"
echo ""
echo "You can now use these directories with Docker volume mounts:"
echo "- shallotbot/data/:/opt/shallot/data/"
echo "- shallotbot/certs/:/opt/shallot/certs/"
echo "- shallotbot/.env:/opt/shallot/.env"
