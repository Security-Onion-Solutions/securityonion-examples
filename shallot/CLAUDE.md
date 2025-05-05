# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build Commands
- **Backend:** `cd backend && poetry install && poetry run uvicorn app.main:app --reload`
- **Frontend:** `cd frontend && npm install && npm run dev`
- **Docker:** `./generate-environment.sh && ./start-docker.sh`
- **Security:** `./scan-security.sh` (scans Python dependencies for vulnerabilities)

## Test Commands
- **Backend Tests:** `cd backend && poetry run pytest`
- **Single Test:** `cd backend && poetry run pytest tests/test_file.py::test_function -v`
- **Frontend Tests:** `cd frontend && npm run test:unit`

## Lint/Type Check
- **Backend:** Black formatting (88 chars), Flake8 linting, MyPy type checking
- **Frontend:** `cd frontend && npm run lint && npm run type-check`
- **Security Check:** `cd backend && poetry run safety check`

## Python Version
- Using Python 3.13 in Docker and for development

## Code Style Guidelines
- **Python:** Use snake_case for variables/functions, PascalCase for classes
- **Imports:** Standard lib → Third-party → Local app (grouped with blank lines)
- **TypeScript:** Use camelCase for variables/functions, PascalCase for components/interfaces
- **Error Handling:** Use try/except with specific exceptions, provide detailed error messages
- **Types:** Use explicit type annotations everywhere (Python and TypeScript)
- **Vue Components:** Use Composition API with TypeScript in Single File Components
- **Documentation:** Google-style docstrings for Python, JSDoc for TypeScript
- **Security:** Always specify minimum versions of dependencies, pin cryptography-related packages