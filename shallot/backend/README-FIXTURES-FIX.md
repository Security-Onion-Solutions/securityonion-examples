# Test Fixtures Fix Summary

This document summarizes the changes made to fix test fixtures for compatibility with GitHub Actions CI.

## Problems

### 1. Missing Fixtures

When tests ran on GitHub Actions CI, failures were occurring with errors like:

```
E fixture 'mock_db' not found
```

This was because some test files defined their own `mock_db` fixture, while others expected it to be available from the shared fixtures in `conftest.py`.

### 2. Missing or Duplicate Fixture Decorators

Some test files had:
- Missing `@pytest.fixture` decorators on fixture functions
- Duplicate `@pytest.fixture` decorators on the same fixture function

For example:
```python
@pytest.fixture
@pytest.fixture  # Duplicate decorator
def mock_user():
    ...
```

## Solutions

### 1. Fixture References Fix

A script `fix_test_fixtures.py` was created to automatically update test files to use the standard `db` fixture that's available in the CI environment, instead of the locally defined `mock_db` fixture.

The script:

1. Scans test files for `mock_db` and other fixture references
2. Changes test function signatures from:
   - `async def test_something(mock_db):`
   - `async def test_something(mock_db: AsyncSession):`
   - `async def test_something(mock_db, other_args):`
   
   to use `db` instead:
   - `async def test_something(db):`
   - `async def test_something(db):`
   - `async def test_something(db, other_args):`

3. Replaces all references to `mock_db` in test functions with `db`
4. Preserves any `mock_db` fixture definitions in the files

### 2. Fixture Decorator Fix

The script was enhanced to handle decorator issues:

1. Adds missing `@pytest.fixture` decorators to fixture definitions
2. In cases of duplicate decorators, we manually fixed them by:
   - Removing duplicate `@pytest.fixture` decorators from fixture functions
   - Ensuring each fixture has exactly one decorator

## Files Fixed

### Files with Updated Fixture References
- `tests/test_auth_api.py`
- `tests/test_settings_api.py`
- `tests/test_users_api.py`
- `tests/test_securityonion.py`
- `tests/test_alerts_command.py` - Added proper @pytest.fixture decorator to the mock_so_client fixture

### Files with Duplicate Decorator Fixes
- `tests/test_auth_api.py` - Removed duplicate decorators on `mock_user` and `mock_superuser` fixtures
- `tests/test_users_api.py` - Removed duplicate decorators on `mock_user`, `mock_superuser`, and `mock_db` fixtures
- `tests/test_settings_api.py` - Removed duplicate decorators on `mock_setting` and `mock_db` fixtures
- `tests/test_securityonion.py` - Removed duplicate decorators on `mock_so_settings` and `mock_httpx_client` fixtures
- `tests/test_alerts_command.py` - Removed duplicate decorator on `mock_so_client` fixture
- `tests/test_commands_core.py` - Removed duplicate decorators on `mock_user`, `mock_chat_user`, `mock_command`, and `mock_db` fixtures, and fixed formatting of `await_mock` fixture

Some files define fixtures but don't actually use them in any test functions, but we still fixed the decorators to ensure proper pytest functionality.

## How to Run the Fix Script

If you encounter fixture-related errors when running tests, you can use the `fix_test_fixtures.py` script:

```bash
# Fix a specific file
./fix_test_fixtures.py path/to/file.py

# Fix all test files in the tests directory
./fix_test_fixtures.py
```

## Testing the Fix

After applying these fixes, run the tests locally with the Docker testing environment to verify they pass:

```bash
./run-tests-docker.sh --test tests/test_auth_api.py::test_get_current_user_valid
```

Or run all tests with:

```bash
./run-tests-docker.sh
```