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

## Test Coverage

### Verifying Coverage Improvements

The project has recently migrated from using `--cov=src` to `--cov=app` for more accurate coverage reporting. This change focuses coverage analysis specifically on the application code rather than including test files or other non-application code.

To verify coverage improvements:

1. **GitHub Actions**: Push your changes to GitHub. The CI pipeline in `.github/workflows/python-test.yml` will automatically run tests with the new `--cov=app` configuration and enforce 100% coverage.

2. **Local Verification**:
   ```bash
   # Run tests with the old configuration
   poetry run pytest -v --cov=src --cov-report=term-missing
   
   # Run tests with the new configuration
   poetry run pytest -v --cov=app --cov-report=term-missing
   ```

3. **Expected Improvements**:
   - More accurate coverage reporting (focusing only on application code)
   - Elimination of false positives from test files being included in coverage
   - Better identification of truly uncovered code paths

The new configuration ensures that only the actual application code in `src/app` is measured for coverage, providing a more meaningful metric of test quality.
