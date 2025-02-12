# Docker Setup Guide

This guide explains how to build and run the Shallot application in Docker with proper volume mounts and configuration.

## Building the Image

```bash
docker build -t shallot:latest .
```

## Running the Container

Basic run command with all necessary volume mounts:

```bash
docker run -d \
  -p 443:443 \
  -v /path/to/data:/app/data \
  -v /path/to/.env:/app/.env \
  -v /path/to/certs:/etc/nginx/ssl \
  --name shallot \
  shallot:latest
```

## Volume Mounts

### 1. Data Directory
- Mount point: `/app/data`
- Purpose: Stores the SQLite database and other persistent data
- Example: `-v /path/to/data:/app/data`
- Permissions: Directory should be writable by the nginx user (UID typically 101)

### 2. Environment File
- Mount point: `/app/.env`
- Purpose: Contains application configuration and secrets
- Example: `-v /path/to/.env:/app/.env`
- Required variables:
  ```
  ENCRYPTION_KEY=<your-secure-encryption-key>
  SECRET_KEY=<your-secure-jwt-secret>
  ```
- See `.env.example` in the root directory for all available options

### 3. SSL Certificates
- Mount point: `/etc/nginx/ssl`
- Purpose: Custom SSL certificates for HTTPS
- Example: `-v /path/to/certs:/etc/nginx/ssl`
- Required files if using custom certificates:
  - `certificate.crt`: SSL certificate
  - `private.key`: Private key
- Note: If no custom certificates are mounted, self-signed certificates will be generated automatically

## Security Notes

1. The container runs HTTPS only (port 443)
2. HTTP traffic (port 80) is automatically redirected to HTTPS
3. The backend is not directly exposed, only accessible through the nginx proxy
4. Default self-signed certificates are provided but should be replaced in production
5. Sensitive data should be properly configured in the .env file
6. Database files are stored in the data volume for persistence

## Setup Options

### Option 1: Automated Setup (Recommended)

Use the provided setup script to automatically generate all required files and directories:

```bash
# Run with default installation directory (/opt/shallot)
sudo ./docker/generate-keys.sh

# Or specify a custom installation directory
sudo ./docker/generate-keys.sh --dir /path/to/install
```

The script will:
1. Create all necessary directories
2. Generate secure encryption keys
3. Create the .env file
4. Generate self-signed SSL certificates
5. Set proper permissions
6. Display the docker run command

### Option 2: Manual Setup

If you prefer to set up manually or need more control:

1. Create directories:
```bash
sudo mkdir -p /opt/shallot/{data,certs}
```

2. Generate environment keys:
```bash
# Generate keys
ENCRYPTION_KEY=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 32)

# Create .env file
cat > /opt/shallot/.env << EOF
ENCRYPTION_KEY=${ENCRYPTION_KEY}
SECRET_KEY=${SECRET_KEY}
EOF

# Set permissions
chmod 600 /opt/shallot/.env
```

3. SSL Certificates:

Option A - Generate self-signed certificates:
```bash
# Generate certificate and key
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /opt/shallot/certs/private.key \
    -out /opt/shallot/certs/certificate.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Set permissions
sudo chmod 644 /opt/shallot/certs/certificate.crt
sudo chmod 600 /opt/shallot/certs/private.key
```

Option B - Use existing certificates:
```bash
# Copy certificates
sudo cp your-cert.crt /opt/shallot/certs/certificate.crt
sudo cp your-key.key /opt/shallot/certs/private.key

# Set permissions
sudo chmod 644 /opt/shallot/certs/certificate.crt
sudo chmod 600 /opt/shallot/certs/private.key
```

4. Set data directory permissions:
```bash
sudo chown -R 101:101 /opt/shallot/data
sudo chmod 755 /opt/shallot/data
```

Note: If no certificates are mounted, the container will automatically generate self-signed certificates during startup.

4. Run the container:
```bash
docker run -d \
  -p 443:443 \
  -v /opt/shallot/data:/app/data \
  -v /opt/shallot/.env:/app/.env \
  -v /opt/shallot/certs:/etc/nginx/ssl \
  --name shallot \
  shallot:latest
```

5. Access the application at `https://localhost`

## Troubleshooting

1. Database permissions:
   - Ensure the data directory is writable by the container
   - Check ownership: `chown -R 101:101 /opt/shallot/data`

2. Certificate issues:
   - Verify certificate files are readable
   - Check nginx logs: `docker logs shallot`

3. Environment variables:
   - Confirm .env file is mounted correctly
   - Verify required variables are set
