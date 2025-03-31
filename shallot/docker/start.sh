#!/bin/sh

# Copyright Security Onion Solutions LLC and/or licensed to Security Onion Solutions LLC under one
# or more contributor license agreements. Licensed under the Elastic License 2.0 as shown at
# https://securityonion.net/license; you may not use this file except in compliance with the
# Elastic License 2.0.
set -e

# Get UID from environment or default to 1000
NGINX_UID=${NGINX_UID:-1000}
NGINX_GID=${NGINX_GID:-1000}

# Function to update nginx user/group if needed (Commented out as handled in Dockerfile for Debian base)
# update_nginx_user() {
#     current_uid=$(id -u nginx 2>/dev/null || echo "0")
#     current_gid=$(id -g nginx 2>/dev/null || echo "0")
#
#     if [ "$current_uid" != "$NGINX_UID" ] || [ "$current_gid" != "$NGINX_GID" ]; then
#         echo "Updating nginx user/group to UID:${NGINX_UID} GID:${NGINX_GID}"
#         # Debian uses useradd/groupadd, handled in Dockerfile
#         # deluser nginx 2>/dev/null || true
#         # delgroup nginx 2>/dev/null || true
#         # addgroup -g ${NGINX_GID} nginx
#         # adduser -D -u ${NGINX_UID} -G nginx -s /sbin/nologin nginx
#     fi
# }

# Function to update permissions
update_permissions() {
    # Removed /opt/shallot as .env is mounted read-only inside it
    dirs="/app/logs/nginx /app/logs/app /etc/nginx/ssl /app/data /usr/share/nginx/html"
    
    for dir in $dirs; do
        echo "Updating permissions for $dir"
        chown -R nginx:nginx "$dir"
        chmod -R u=rwX,g=rX,o=rX "$dir"
    done
    
    # Ensure log files exist and are writable
    touch /app/logs/nginx/access.log /app/logs/nginx/error.log
    touch /app/logs/app/backend.log /app/logs/app/docker.log
    chown nginx:nginx /app/logs/nginx/access.log /app/logs/nginx/error.log
    chown nginx:nginx /app/logs/app/backend.log /app/logs/app/docker.log
    chmod 644 /app/logs/nginx/access.log /app/logs/nginx/error.log
    chmod 644 /app/logs/app/backend.log /app/logs/app/docker.log
}

echo "$(date '+%Y-%m-%d %H:%M:%S') Container started" >> /app/logs/app/docker.log

# Update nginx user if needed
# update_nginx_user # Handled in Dockerfile

# Update permissions
update_permissions

# Start the Python backend with logging configuration
echo "Starting FastAPI backend..." >> /app/logs/app/docker.log
cd /app
python3 -m uvicorn src.app.main:app --host 0.0.0.0 --port 8000 >> /app/logs/app/backend.log 2>&1 &

# Wait for backend to be ready
echo "Waiting for backend to be ready..." >> /app/logs/app/docker.log
while ! nc -z localhost 8000; do
  sleep 1
done
echo "Backend is ready!" >> /app/logs/app/docker.log

# Start nginx without daemon mode
echo "$(date '+%Y-%m-%d %H:%M:%S') Starting nginx..." >> /app/logs/app/docker.log
nginx -g 'daemon off;' >> /app/logs/app/docker.log 2>&1
