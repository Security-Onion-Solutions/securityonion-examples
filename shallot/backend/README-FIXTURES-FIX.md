# Test Fixtures Fix Summary

This document summarizes the changes made to fix test fixtures for compatibility with GitHub Actions CI.

## Problem

When tests ran on GitHub Actions CI, failures were occurring with errors like:

```
E fixture 'mock_db' not found
```

This was because some test files defined their own `mock_db` fixture, while others expected it to be available from the shared fixtures in `conftest.py`.

## Solution

A script `fix_test_fixtures.py` was created to automatically update test files to use the standard `db` fixture that's available in the CI environment, instead of the locally defined `mock_db` fixture.

The script:

1. Scans test files for `mock_db` references
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

## Files Fixed

The following files were updated:
- `tests/test_auth_api.py`
- `tests/test_settings_api.py`
- `tests/test_users_api.py`
- `tests/test_securityonion.py`

Some files like `tests/test_commands_core.py` define a `mock_db` fixture but don't actually use it in any test functions, so no changes were needed there.

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