#!/usr/bin/env python3
"""
Script to fix async tests for Python 3.13 compatibility.

This script helps to fix Python 3.13 AsyncMock compatibility issues by
finding and fixing issues where the automatic fixers introduced redundant
awaitable wrapping.
"""
import re
import sys
from pathlib import Path


def fix_test_file(file_path):
    """Fixes async test compatibility issues in test files."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Store original content
    original_content = content
    
    # Fix 1: Remove duplicate fixture decorator from await_mock function
    content = re.sub(
        r"@pytest\.fixture\s+\n\s*def await_mock\(return_value\):",
        r"def await_mock(return_value):",
        content
    )
    
    # Fix 2: Remove duplicate MagicMock imports
    content = re.sub(
        r"from unittest\.mock import .*MagicMock, MagicMock.*",
        r"from unittest.mock import AsyncMock, MagicMock, patch",
        content
    )
    
    # Fix 3: Clean up excessive await_mock chains
    # Find patterns like:
    # mock_result.scalar_one_or_none.return_value = await_mock(mock_result.scalar_one_or_none.return_value)
    # mock_result.scalar_one_or_none.return_value = await_mock(mock_result.scalar_one_or_none.return_value)
    # Keep only one
    await_mock_pattern = r"(\s+)([a-zA-Z0-9_.]+)\.return_value = await_mock\(\2\.return_value\)\n\n\1\2\.return_value = await_mock\(\2\.return_value\)"
    while re.search(await_mock_pattern, content):
        content = re.sub(
            await_mock_pattern,
            r"\1\2.return_value = await_mock(\2.return_value)",
            content
        )
    
    # Fix 4: Clean up groups of redundant awaits with empty lines between them
    await_mock_chain_pattern = r"(\s+)([a-zA-Z0-9_.]+)\.return_value = await_mock\(\2\.return_value\)\n\n+\1\2\.return_value = await_mock\(\2\.return_value\)"
    while re.search(await_mock_chain_pattern, content):
        content = re.sub(
            await_mock_chain_pattern,
            r"\1\2.return_value = await_mock(\2.return_value)",
            content
        )
    
    # Fix 5: Update mock_db fixture to properly handle execute method
    content = re.sub(
        r"@pytest\.fixture\ndef mock_db\(\):\s+\"\"\"Create a mock database session\.\"\"\"\s+return AsyncMock\(spec=AsyncSession\)",
        r"@pytest.fixture\ndef mock_db():\n    \"\"\"Create a mock database session.\"\"\"\n    db = AsyncMock(spec=AsyncSession)\n    # In Python 3.13, we need to mock execute specially\n    mock_execute = AsyncMock()\n    db.execute = mock_execute\n    return db",
        content
    )
    
    # Fix 6: Add helpful comments for await_mock calls
    content = re.sub(
        r"(\s+)([a-zA-Z0-9_.]+)\.return_value = await_mock\(\2\.return_value\)",
        r"\1\2.return_value = await_mock(\2.return_value)  # Make awaitable for Python 3.13",
        content
    )
    
    # Fix 7: Update async test functions to handle asyncio in Python 3.13
    # For test_api_refresh_token_endpoint and similar test functions
    content = re.sub(
        r"@pytest\.mark\.asyncio\nasync def (test_api_[a-zA-Z_]+)\(",
        r"def \1(",
        content
    )
    
    # Write back only if changed
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    
    return False


def main():
    """Main function to fix async test compatibility issues."""
    print("Starting Python 3.13 AsyncMock compatibility fixes...")
    test_dir = Path("tests")
    
    fixed_files = 0
    
    for test_file in test_dir.glob("**/*.py"):
        if fix_test_file(test_file):
            fixed_files += 1
            print(f"  Fixed test file: {test_file}")
    
    print(f"Fixed {fixed_files} test files")
    print("Python 3.13 AsyncMock compatibility fixes complete!")


if __name__ == "__main__":
    main()