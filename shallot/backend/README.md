# Security Onion Chat Bot - Backend

The backend service for the Security Onion Chat Bot, providing a bridge between chat platforms and the Security Onion API.

## Features

- FastAPI-based REST API
- Chat platform integration (Slack/Teams/Discord)
- Security Onion API integration
- Role-based access control
- Encrypted storage for sensitive data
- Command processing engine
- WebSocket support for real-time updates

## Prerequisites

- Python 3.8+
- Poetry (Python package manager)
- Git

## Setup & Development

1. Clone the repository:
```bash
git clone <repository-url>
cd backend
```

2. Start the backend:
```bash
./scripts/start-backend.sh
```

This script will:
- Install dependencies if needed
- Create a .env file with encryption key if not exists
- Run tests with coverage reporting
- Run type checking and linting
- Start the development server

## Environment Configuration

The `.env` file only contains the encryption key used for sensitive data in SQLite:
```bash
# This key is used for encrypting sensitive data in the SQLite database
ENCRYPTION_KEY=<generated-automatically>
```

All other configuration (API keys, tokens, etc.) is stored securely in the SQLite database and managed through the web interface.

## Project Structure

```
backend/
├── src/
│   └── app/
│       ├── main.py          # FastAPI application
│       ├── config.py        # Settings management
│       ├── database.py      # Database configuration
│       ├── models/          # SQLAlchemy models
│       ├── schemas/         # Pydantic schemas
│       ├── api/             # API endpoints
│       ├── core/            # Core functionality
│       ├── services/        # Business logic
│       └── utils/           # Utility functions
├── tests/                   # Test files
├── scripts/
│   └── start-backend.sh     # Development script
├── pyproject.toml          # Poetry configuration
└── README.md               # This file
```

## API Documentation

When the server is running, access:
- OpenAPI documentation: http://localhost:8000/docs
- ReDoc documentation: http://localhost:8000/redoc

## Contributing

1. Ensure all tests pass before submitting changes
2. Follow the existing code style (enforced by black/flake8)
3. Add tests for new functionality
4. Update documentation as needed
