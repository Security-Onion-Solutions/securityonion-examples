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

# Install and configure poetry with latest version
RUN pip install --no-cache-dir "poetry>=1.8.0" && \
    poetry config virtualenvs.create false

# Update pip first
RUN pip install --no-cache-dir --upgrade pip

# Verify package directory exists and install dependencies with latest versions
RUN ls -la && \
    poetry update --only main --no-interaction --no-ansi && \
    poetry install --only main --no-interaction --no-ansi

# Check for security vulnerabilities
RUN pip install --no-cache-dir safety && \
    (poetry export --format=requirements.txt > /tmp/requirements.txt && \
     safety check -r /tmp/requirements.txt || echo "Security issues found. Review during build.")

# Stage 3: Generate SSL Certificate
FROM alpine:latest AS cert-generator
RUN apk add --no-cache openssl
WORKDIR /certs
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout private.key -out certificate.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Stage 4: Final Image
FROM python:3.13-alpine

# Install nginx and create required directories
RUN apk add --no-cache nginx && \
    mkdir -p /var/cache/nginx /etc/nginx/conf.d

# Add support for dynamic UID/GID
ARG NGINX_UID=1000
ARG NGINX_GID=1000

# Create nginx user with dynamic UID/GID
RUN addgroup -g ${NGINX_GID} nginx || true && \
    adduser -D -u ${NGINX_UID} -G nginx -s /sbin/nologin nginx || true
WORKDIR /app

# Install system dependencies including build tools for matrix-nio
RUN apk add --no-cache \
    netcat-openbsd \
    gcc \
    g++ \
    make \
    cmake \
    musl-dev \
    libffi-dev \
    openssl-dev

# Update pip first
RUN pip3 install --no-cache-dir --upgrade pip

# Install Python packages in groups to better handle dependencies with latest versions
RUN pip3 install --no-cache-dir --upgrade \
    uvicorn>=0.24.0 \
    fastapi>=0.104.0 \
    sqlalchemy>=2.0.23 \
    pydantic>=2.5.0 \
    pydantic-settings>=2.1.0 \
    python-multipart>=0.0.9 \
    httpx>=0.25.0 \
    websockets>=12.0 \
    python-dotenv>=1.0.0 \
    aiosqlite>=0.19.0 \
    email-validator>=2.1.0 \
    dnspython>=2.4.2

# Install cryptography-related packages with latest secure versions
RUN pip3 install --no-cache-dir --upgrade \
    cryptography>=43.0.1 \
    python-jose[cryptography]>=3.3.0 \
    passlib[bcrypt]>=1.7.4 \
    bcrypt>=4.0.0

# Install chat platform packages with latest versions
RUN pip3 install --no-cache-dir --upgrade \
    discord.py>=2.4.0 \
    slack-sdk>=3.23.0 \
    botbuilder-core>=4.14.0

# Install libolm which is required for Matrix E2E encryption
RUN apk add --no-cache git

# Install Matrix-related packages with latest versions
# First try to install python-olm separately
RUN pip3 install --no-cache-dir --upgrade python-olm>=3.2.15 || \
    echo "Warning: Failed to install python-olm, e2e encryption may not be available"

# Then install matrix-nio, try with e2e support first, fall back to base if it fails
RUN pip3 install --no-cache-dir --upgrade matrix-nio[e2e]>=0.24.0 || \
    (echo "Warning: Installing matrix-nio without e2e support" && \
     pip3 install --no-cache-dir --upgrade matrix-nio>=0.24.0)

# Install remaining packages with latest versions
RUN pip3 install --no-cache-dir --upgrade \
    alembic>=1.12.0 \
    python-whois>=0.8.0

# Install security scanning tools
RUN pip3 install --no-cache-dir safety && \
    pip3 freeze > /tmp/requirements.txt && \
    safety check -r /tmp/requirements.txt || echo "Security issues found in final image. Review during build."

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
