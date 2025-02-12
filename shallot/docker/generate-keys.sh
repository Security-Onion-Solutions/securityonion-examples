#!/bin/bash

# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.
set -e

# Default installation directory
INSTALL_DIR="/opt/shallot"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create necessary directories
echo "Creating directories..."
mkdir -p "${INSTALL_DIR}"/{data,certs}

# Generate environment file
echo "Generating .env file..."
ENCRYPTION_KEY=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 32)

cat > "${INSTALL_DIR}/.env" << EOF
# Generated on $(date)
ENCRYPTION_KEY=${ENCRYPTION_KEY}
SECRET_KEY=${SECRET_KEY}
EOF

# Generate self-signed certificates
echo "Generating self-signed certificates..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "${INSTALL_DIR}/certs/private.key" \
    -out "${INSTALL_DIR}/certs/certificate.crt" \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Set proper permissions
echo "Setting permissions..."
chmod 644 "${INSTALL_DIR}/certs/certificate.crt"
chmod 600 "${INSTALL_DIR}/certs/private.key"
chmod 600 "${INSTALL_DIR}/.env"

# Create data directory with proper permissions
chown -R 101:101 "${INSTALL_DIR}/data"
chmod 755 "${INSTALL_DIR}/data"

echo "Setup complete!"
echo "Installation directory: ${INSTALL_DIR}"
echo
echo "Generated files:"
echo "- Environment file: ${INSTALL_DIR}/.env"
echo "- SSL certificate: ${INSTALL_DIR}/certs/certificate.crt"
echo "- SSL private key: ${INSTALL_DIR}/certs/private.key"
echo
echo "You can now run the container with:"
echo "docker run -d \\"
echo "  -p 443:443 \\"
echo "  -v ${INSTALL_DIR}/data:/app/data \\"
echo "  -v ${INSTALL_DIR}/.env:/app/.env \\"
echo "  -v ${INSTALL_DIR}/certs:/etc/nginx/ssl \\"
echo "  --name shallot \\"
echo "  shallot:latest"
