# Testing Documentation

This document provides information about the test suite for the Shallot backend.

## Test Structure

Tests are organized into several categories:

1. **Service Tests**: Tests for service layer functions
   - `test_chat_users_service.py` and `test_chat_users_service_complete.py`
   - `test_settings_service.py` and `test_settings_service_complete.py` 
   - `test_chat_permissions.py`
   - `test_users_service.py`

2. **Model Tests**: Tests for models and their methods/properties
   - `test_settings_model.py`

3. **Core Module Tests**: Tests for core functionality
   - `test_securityonion.py` and `test_securityonion_complete.py`

4. **Integration Tests**: Tests that verify multiple components working together
   - Various test files that span multiple components

## Running Tests

There are several ways to run the tests:

### Local Testing

To run tests locally with Poetry:

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_users_service.py

# Run with coverage
poetry run pytest --cov=src/app --cov-report=term
```

### Docker Testing

To run tests in a Docker container with Python 3.13:

```bash
# Build and run tests in Docker
./run-tests-docker.sh

# The coverage report will be available in ./coverage/htmlcov/index.html
```

### Full Coverage Testing

A script is provided to run a comprehensive test suite with detailed coverage reporting:

```bash
# Run the full test suite with coverage
./run-full-coverage.sh

# The coverage report will be available in ./coverage/htmlcov/index.html
```

## Python 3.13 Compatibility

Tests are designed to be compatible with Python 3.13's stricter coroutine handling. A fix script is available to update tests:

```bash
# Apply Python 3.13 compatibility fixes
python fix_async_tests.py
```

For details on the Python 3.13 compatibility issues and solutions, see `README-ASYNC-FIX.md`.

## Coverage Reports

The test suite generates coverage reports in multiple formats:

- **Terminal**: Shows coverage statistics in the console
- **HTML**: Interactive HTML report in `./coverage/htmlcov/index.html`
- **JSON**: Machine-readable data in `./coverage/coverage.json`

## Adding New Tests

When adding new tests:

1. Follow the existing patterns for similar components
2. Ensure Python 3.13 compatibility with coroutine handling
3. Use the test fixtures in `conftest.py` for database and other shared resources
4. Add sufficient tests to reach 100% code coverage
5. Run the tests with coverage to verify the coverage increase

## Troubleshooting

### SQLAlchemy Text Queries

When using direct SQL queries with SQLAlchemy, you must use the `text()` function:

```python
from sqlalchemy import text
result = await db.execute(text("SELECT * FROM users"))
```

### AsyncMock Coroutines

When mocking asynchronous functions, use the `await_mock()` helper:

```python
from tests.utils import await_mock
mock_result = AsyncMock()
mock_result.scalar_one.return_value = await_mock(5)
```

### Test Database

Tests use an in-memory SQLite database. Remember that some SQLite features may differ from production databases.