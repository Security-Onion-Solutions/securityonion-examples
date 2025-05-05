# Stage 1: Build Frontend
FROM node:18 AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
RUN npm install -D @types/node
COPY frontend/ .
RUN npm run build

# Stage 2: Build Backend
FROM python:3.13-slim AS backend-builder
WORKDIR /app

# Copy the entire backend directory
COPY backend/ .

# Install system dependencies required for building Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install and configure poetry
RUN pip install "poetry==1.6.1" && \
    poetry config virtualenvs.create false

# Verify package directory exists and install dependencies
RUN ls -la # Removed poetry install from builder stage, handled in final stage via pip

# Stage 3: Generate SSL Certificate
FROM alpine:latest AS cert-generator
RUN apk add --no-cache openssl
WORKDIR /certs
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout private.key -out certificate.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Stage 4: Final Image
FROM python:3.13-slim

# Add support for dynamic UID/GID
ARG NGINX_UID=1000
ARG NGINX_GID=1000

# Install Nginx and necessary tools for runtime and pip installs
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    nginx \
    netcat-openbsd \
    build-essential \
    gcc \
    libc6-dev \
    libffi-dev \
    openssl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Python 3.13 and pip are included in the base image.
# build-essential, gcc, libc6-dev, libffi-dev, openssl installed above.
# netcat-openbsd also installed above.
# Install Python packages in groups to better handle dependencies
RUN pip install \
    uvicorn \
    fastapi \
    sqlalchemy \
    pydantic \
    pydantic-settings \
    python-multipart \
    httpx \
    websockets \
    python-dotenv \
    aiosqlite \
    email-validator \
    dnspython

# Install cryptography-related packages
RUN pip install \
    cryptography \
    python-jose[cryptography] \
    passlib[bcrypt]

# Install chat platform packages
RUN pip install \
    discord.py \
    slack-sdk \
    botbuilder-core

# Install Matrix-related packages
RUN pip install \
    matrix-nio

# Install remaining packages
RUN pip install \
    alembic \
    python-whois

# Set Python path
ENV PYTHONPATH=/app/src

# Copy backend and dependencies
COPY --from=backend-builder /usr/local/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages/
COPY backend/src/app /app/src/app
COPY docs /docs

# Verify Python can find uvicorn
RUN python3 -c "import uvicorn" && \
    python3 -c "import fastapi"

# Copy frontend build
COPY --from=frontend-builder /app/dist /usr/share/nginx/html

# Copy SSL certificates
COPY --from=cert-generator /certs/private.key /etc/nginx/ssl/private.key
COPY --from=cert-generator /certs/certificate.crt /etc/nginx/ssl/certificate.crt

# Create necessary directories and set permissions
# Create nginx user/group with dynamic UID/GID (Debian way)
# Use -r for system user/group. Add || commands for idempotency if needed.
RUN groupadd -r -g ${NGINX_GID} nginx || groupmod -g ${NGINX_GID} nginx && \
    useradd -r -u ${NGINX_UID} -g nginx -s /sbin/nologin nginx || usermod -u ${NGINX_UID} -g ${NGINX_GID} nginx

# Create necessary directories and set permissions
RUN mkdir -p /etc/nginx/ssl /app/data /opt/shallot /var/log/nginx /var/cache/nginx /etc/nginx/sites-enabled /var/lib/nginx/tmp && \
    chown -R nginx:nginx /app/data /opt/shallot /var/log/nginx /var/cache/nginx /etc/nginx/ssl /etc/nginx/sites-enabled /var/lib/nginx && \
    chmod -R 755 /app/data /opt/shallot /var/log/nginx /var/cache/nginx /etc/nginx/ssl /etc/nginx/sites-enabled /var/lib/nginx && \
    chmod 777 /var/lib/nginx/tmp # Ensure nginx can write here

# Create symlink for .env file
RUN ln -s /opt/shallot/.env /app/.env

# Create nginx cache directories with proper permissions
RUN mkdir -p /var/cache/nginx/client_temp \
            /var/cache/nginx/proxy_temp \
            /var/cache/nginx/fastcgi_temp \
            /var/cache/nginx/uwsgi_temp \
            /var/cache/nginx/scgi_temp && \
    chmod 777 -R /var/cache/nginx

# Create logs directory structure
RUN mkdir -p /app/logs/nginx /app/logs/app && \
    chown -R nginx:nginx /app/logs && \
    chmod -R 755 /app/logs

# Document volume mount points
VOLUME ["/app/data", "/etc/nginx/ssl", "/app/logs"]

# Symlink nginx logs to our logs directory
RUN ln -sf /app/logs/nginx/access.log /var/log/nginx/access.log && \
    ln -sf /app/logs/nginx/error.log /var/log/nginx/error.log

# Copy nginx configurations and startup script
# Main Nginx config
COPY docker/main_nginx.conf /etc/nginx/nginx.conf
# Site config
COPY docker/nginx.conf /etc/nginx/sites-available/default
# Enable site
RUN ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8443

CMD ["/start.sh"]
