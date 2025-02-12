# Stage 1: Build Frontend
FROM node:18 AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
RUN npm install -D @types/node
COPY frontend/ .
RUN npm run build

# Stage 2: Build Backend
FROM python:3.11-slim AS backend-builder
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
RUN ls -la && \
    poetry install --only main --no-interaction --no-ansi

# Stage 3: Generate SSL Certificate
FROM alpine:latest AS cert-generator
RUN apk add --no-cache openssl
WORKDIR /certs
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout private.key -out certificate.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Stage 4: Final Image
FROM nginx:alpine

# Add support for dynamic UID/GID
ARG NGINX_UID=1000
ARG NGINX_GID=1000

# Create nginx user with dynamic UID/GID
RUN deluser nginx && \
    addgroup -g ${NGINX_GID} nginx && \
    adduser -D -u ${NGINX_UID} -G nginx -s /sbin/nologin nginx
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    netcat-openbsd \
    gcc \
    musl-dev \
    python3-dev \
    libffi-dev \
    openssl-dev

# Install Python packages in groups to better handle dependencies
RUN pip3 install --break-system-packages \
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
RUN pip3 install --break-system-packages \
    cryptography \
    python-jose[cryptography] \
    passlib[bcrypt]

# Install chat platform packages
RUN pip3 install --break-system-packages \
    discord.py \
    slack-sdk \
    botbuilder-core

# Install Matrix-related packages
RUN pip3 install --break-system-packages \
    matrix-nio

# Install remaining packages
RUN pip3 install --break-system-packages \
    alembic \
    python-whois

# Set Python path
ENV PYTHONPATH=/app/src

# Copy backend and dependencies
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
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
RUN mkdir -p /etc/nginx/ssl /app/data /opt/shallot && \
    chown -R nginx:nginx /app/data /opt/shallot /var/log/nginx /var/cache/nginx /etc/nginx/ssl /etc/nginx/conf.d && \
    chmod -R 755 /app/data /opt/shallot /var/log/nginx /var/cache/nginx /etc/nginx/ssl /etc/nginx/conf.d

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
COPY docker/main_nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8443

CMD ["/start.sh"]
