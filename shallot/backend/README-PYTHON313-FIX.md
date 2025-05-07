# Python 3.13 AsyncMock Compatibility Fix

## Overview

This document provides guidance on fixing Python 3.13 compatibility issues in tests that use AsyncMock objects.

## Issue Description

In Python 3.13, there are significant changes in how coroutines are handled, which affects how AsyncMock objects work in tests:

1. Coroutines must be explicitly awaited
2. Mocked methods need to return awaitable objects
3. Chained methods (like `db.execute().scalar_one()`) require careful handling

Common errors include:
- `AssertionError: assert <coroutine object AsyncMockMixin._execute_mock_call at 0x...> == [expected value]`
- `TypeError: object AsyncMock can't be used in 'await' expression`
- `RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited`

## Solution Approach

We've adopted several approaches to fix these issues:

1. Created helper functions in `tests/utils.py`:
   - `await_mock(return_value)`: Makes a value awaitable
   - `make_mock_awaitable(mock_obj, method_name)`: Makes a mock method's return value awaitable
   - `setup_mock_db()`: Creates a properly configured mock database session

2. Updated test files to:
   - Create properly mocked database sessions
   - Ensure mock methods return awaitable values
   - Handle chained method calls correctly

3. Fixed patterns like:
   ```python
   # Before: Works in Python 3.10-3.12 but fails in 3.13
   mock_result = MagicMock()
   mock_result.scalar_one.return_value = 5
   db.execute.return_value = mock_result
   
   # After: Works in Python 3.13
   mock_result = MagicMock()
   mock_result.scalar_one.return_value = 5
   mock_result.scalar_one.return_value = await_mock(mock_result.scalar_one.return_value)
   db.execute.return_value = await_mock(mock_result)
   ```

## Common Fix Patterns

1. **For database query mocking**:
   ```python
   # Create database session mock
   from tests.utils import setup_mock_db
   db = setup_mock_db()
   
   # Setup mock query result
   mock_result = MagicMock()
   mock_result.scalar_one_or_none.return_value = expected_value
   mock_result.scalar_one_or_none.return_value = await_mock(mock_result.scalar_one_or_none.return_value)
   db.execute.return_value = await_mock(mock_result)
   ```

2. **For test fixtures**:
   ```python
   @pytest.fixture
   def mock_db():
       """Create a mock database session."""
       from tests.utils import setup_mock_db
       return setup_mock_db()
   ```

3. **For making existing mocks awaitable**:
   ```python
   # Make an existing mock method awaitable
   from tests.utils import make_mock_awaitable
   make_mock_awaitable(mock_obj, "method_name")
   ```

## Test Design Recommendations

1. Prefer creating fresh mocks for each test instead of relying on fixtures that may be modified
2. Use the helper functions consistently for all awaitable mocks
3. Be explicit about which methods need to return awaitable values
4. Verify changes by running tests with Python 3.13

## References

- [Python 3.13 Release Notes](https://docs.python.org/3.13/whatsnew/3.13.html)
- [Asyncio Changes in Python 3.13](https://docs.python.org/3.13/whatsnew/3.13.html#asyncio)
- [unittest.mock Documentation](https://docs.python.org/3.13/library/unittest.mock.html)