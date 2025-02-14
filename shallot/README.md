# Shallot - Security Onion Chat Bot

A chat integration system for Security Onion that enables teams to interact with their security monitoring system through various chat platforms including Matrix, Slack, and Discord.

## Warnings and Disclaimers

This is just an EXAMPLE and is TOTALLY UNSUPPORTED!

This is not intended for production use!

If this breaks anything you get to keep BOTH pieces!

## Features

- **Multi-Platform Support**
  - Matrix (unencrypted)
  - Slack
  - Discord

- **Command System**
  - Prefix-based command recognition
  - Asynchronous command processing
  - Platform-agnostic command handling
  - Customizable command prefix

- **Alert System**
  - Configurable alert notifications
  - Dedicated alert rooms
  - Formatted alert messages
  - Real-time delivery

- **Security Features**
  - Platform-specific authentication
  - API access control
  - User permission management
  - Secure token storage

## Quick Start

1. Clone the Security Onion Examples repository:
```bash
git clone https://github.com/Security-Onion-Solutions/securityonion-examples.git
cd securityonion-examples/shallot
```

2. Generate environment configuration:
```bash
./generate-environment.sh
```
This will create a `shallotbot` directory containing:
- `.env` file with secure randomly generated keys for database encryption and JWT tokens
- `certs/` directory with self-signed SSL certificates for HTTPS
- `data/` directory for persistent storage
These directories are structured to map directly to the Docker container paths:
- `shallotbot/data/:/opt/shallot/data/`
- `shallotbot/certs/:/opt/shallot/certs/`
- `shallotbot/.env:/opt/shallot/.env`

3. Using Docker (recommended):
```bash
docker compose up -d
```

4. Manual Setup:
   - See [Backend Setup](#backend-setup) and [Frontend Setup](#frontend-setup) sections below

## Backend Setup

1. Install Python dependencies:
```bash
cd backend
poetry install
```

2. Initialize the database:
```bash
poetry run alembic upgrade head
```

3. Start the backend server:
```bash
poetry run uvicorn app.main:app --reload
```

## Frontend Setup

1. Install Node.js dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

## Documentation

- [Setup Guide](docs/setup.html)
- [API Documentation](docs/openapi.json)
- [Contributing Guidelines](CONTRIBUTING.md)

## Development

### Tech Stack

- **Backend**
  - FastAPI (API framework)
  - SQLAlchemy (Database ORM)
  - matrix-nio (Matrix client)
  - Poetry (Dependency management)

- **Frontend**
  - Vue 3
  - Vuetify
  - TypeScript
  - Vite

### Testing

Backend tests:
```bash
cd backend
poetry run pytest
```

Frontend tests:
```bash
cd frontend
npm run test
```

## Docker Deployment

1. Generate the environment and SSL certificates:
```bash
./generate-environment.sh
```
This creates the required directory structure and files in `shallotbot/`.

2. Build and run the container:
```bash
./start-docker.sh
```
This script will:
- Verify the required files exist
- Build the Docker image
- Prompt for the HTTPS port (default: 443)
- Start the container with proper volume mounts:
  - `shallotbot/data/:/opt/shallot/data/`
  - `shallotbot/certs/:/opt/shallot/certs/`
  - `shallotbot/.env:/opt/shallot/.env`

See [docker/README.md](docker/README.md) for additional deployment options.

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the ELv2 License - see the [LICENSE](LICENSE) file for details.
