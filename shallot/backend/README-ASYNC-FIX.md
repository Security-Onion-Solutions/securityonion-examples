# Python 3.13 AsyncMock Compatibility Fix

## Overview

Python 3.13 introduced stricter handling of coroutines and awaitable objects, which affects how AsyncMock objects work in unit tests. This repository includes a script (`fix_async_tests.py`) to automatically fix these compatibility issues.

## The Issue

In Python 3.13, when using `AsyncMock` objects:
- Coroutines must be explicitly awaited
- Return values of async methods need to be awaitable themselves
- Mock objects that are returned from async methods need special handling

Common errors you might see:
- `AssertionError: assert <coroutine object AsyncMockMixin._execute_mock_call at 0x7c294f701840> == 5`
- `TypeError: object AsyncMock can't be used in 'await' expression`
- `RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited`

## The Solution

The `fix_async_tests.py` script applies the following fixes:

1. Replaces some `AsyncMock` instances with `MagicMock` where awaiting is not necessary
2. Makes return values of async methods awaitable by wrapping them in a helper function
3. Adds a helper function `await_mock()` to make values awaitable in async contexts
4. Fixes direct awaits of methods that should not be awaited (like `scalars().all()`)

## Usage

To fix your tests for Python 3.13 compatibility:

```bash
# Run the script to fix all tests
python fix_async_tests.py

# Run tests with Python 3.13
poetry run pytest
```

## Technical Details

The primary pattern that needs fixing in tests is the handling of AsyncMock return values. In Python 3.13, these need to be made explicitly awaitable:

```python
# Before: This works in Python 3.10-3.12 but fails in 3.13
mock_result = AsyncMock()
mock_result.scalar_one.return_value = 5
mock_db.execute.return_value = mock_result

# After: This works in Python 3.13
mock_result = AsyncMock()
mock_result.scalar_one.return_value = 5
mock_result.scalar_one.return_value = await_mock(mock_result.scalar_one.return_value)
mock_db.execute.return_value = mock_result
mock_db.execute.return_value = await_mock(mock_db.execute.return_value)

# Helper function added to test files
def await_mock(return_value):
    """Helper function to make mock return values awaitable in Python 3.13."""
    async def _awaitable():
        return return_value
    return _awaitable()
```

## Docker Testing

A Docker-based test environment is available to test with Python 3.13 without needing to install it locally:

```bash
./run-tests-docker.sh
```

This script builds a Docker container with Python 3.13, runs the tests, and generates a coverage report.

## References

- [Python 3.13 Release Notes](https://docs.python.org/3.13/whatsnew/3.13.html)
- [Asyncio Changes in Python 3.13](https://docs.python.org/3.13/whatsnew/3.13.html#asyncio)
- [unittest.mock Documentation](https://docs.python.org/3.13/library/unittest.mock.html)