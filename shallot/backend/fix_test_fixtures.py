#!/usr/bin/env python3
"""
Script to fix fixture usage in test files to ensure compatibility with the existing pattern.
This script updates tests to use the db fixture instead of mock_db fixture.
"""
import re
import sys
from pathlib import Path


def fix_test_file(file_path):
    """Fix fixture usage in test files for GitHub Actions compatibility."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Store original content
    original_content = content
    
    # Check if we need to make any changes
    if "mock_db" not in content and "mock_so_client" not in content:
        return False
    
    print(f"DEBUG: Processing {file_path}")
    
    # Fix different test function definition patterns
    
    # Handle pattern: async def test_name(mock_db: AsyncSession):
    content = re.sub(
        r"async def (test_\w+)\(mock_db: AsyncSession\):",
        r"async def \1(db):",
        content
    )
    
    # Handle pattern: async def test_name(mock_db):
    content = re.sub(
        r"async def (test_\w+)\(mock_db\):",
        r"async def \1(db):",
        content
    )
    
    # Handle pattern: async def test_name(mock_db, other_args):
    content = re.sub(
        r"async def (test_\w+)\(mock_db(,\s+[^)]+)\):",
        r"async def \1(db\2):",
        content
    )
    
    # Fix missing @pytest.fixture decorators
    # Look for fixture definitions without the decorator
    fixture_def_pattern = r"\ndef (mock_\w+)\(\):"
    fixture_defs = re.findall(fixture_def_pattern, content)
    
    for fixture_name in fixture_defs:
        print(f"DEBUG: Found fixture definition for {fixture_name}")
        # Check if it's missing the decorator
        fixture_def_line = re.search(r"\ndef " + fixture_name + r"\(\):", content)
        if fixture_def_line:
            line_index = content[:fixture_def_line.start()].count('\n')
            lines = content.split('\n')
            
            # Check if the line before contains @pytest.fixture
            if line_index > 0 and "@pytest.fixture" not in lines[line_index-1]:
                print(f"DEBUG: Adding missing @pytest.fixture decorator for {fixture_name}")
                lines.insert(line_index, "@pytest.fixture")
                content = '\n'.join(lines)
                print(f"DEBUG: Added decorator for {fixture_name}")
    
    # For test_commands_core.py and similar files, they define their own mock_db fixture
    # but use it in test functions. We need to handle this case specially.
    if "def mock_db():" in content:
        print(f"DEBUG: Found mock_db fixture definition in {file_path}")
        
        # Let's check for test functions that use the mock_db fixture
        test_functions_fixed = 0
        
        # Extract test function definitions
        test_function_pattern = r"(async def test_[\w_]+\([^)]*mock_db[^)]*\):)"
        test_functions = re.findall(test_function_pattern, content)
        
        if test_functions:
            print(f"DEBUG: Found {len(test_functions)} test functions using mock_db")
            for func in test_functions:
                print(f"DEBUG: Found function: {func}")
        else:
            print(f"DEBUG: No test functions found using mock_db pattern")
        
        # Process line by line to catch all possible patterns
        lines = []
        in_fixture_def = False
        for line in content.split('\n'):
            # Track if we're in the mock_db fixture definition
            if "@pytest.fixture" in line and "def mock_db" in content.split('\n')[content.split('\n').index(line) + 1]:
                in_fixture_def = True
            elif in_fixture_def and "def " in line and "mock_db" not in line:
                in_fixture_def = False
            
            # Don't modify the fixture definition
            if in_fixture_def:
                lines.append(line)
                continue
            
            # Replace references in test function signatures and bodies
            if "async def test_" in line and "mock_db" in line:
                print(f"DEBUG: Replacing in test function signature: {line}")
                line = line.replace("mock_db", "db")
                test_functions_fixed += 1
            elif "mock_db" in line and "def mock_db" not in line:
                print(f"DEBUG: Replacing in function body: {line}")
                line = line.replace("mock_db", "db")
            
            lines.append(line)
        
        content = '\n'.join(lines)
        print(f"DEBUG: Fixed {test_functions_fixed} test functions")
    else:
        # For files that don't define the mock_db fixture,
        # replace all references to mock_db with db
        lines = []
        for line in content.split('\n'):
            # Replace mock_db with db in test functions
            if "async def test_" in line:
                if "mock_db" in line:
                    print(f"DEBUG: Replacing in test function: {line}")
                    line = line.replace("mock_db", "db")
            elif "mock_db" in line and "def mock_db" not in line:
                print(f"DEBUG: Replacing in function body: {line}")
                line = line.replace("mock_db", "db")
            
            lines.append(line)
        
        content = '\n'.join(lines)
    
    # Fix any double await_mock calls
    content = re.sub(
        r"await_mock\(await_mock\(([^)]+)\)\)",
        r"await_mock(\1)",
        content
    )
    
    # Write back only if changed
    if content != original_content:
        print(f"DEBUG: File content changed, writing back")
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    else:
        print(f"DEBUG: No changes needed for {file_path}")
    
    return False


def main():
    """Main function to fix test files."""
    print("Starting test fixture compatibility fixes...")
    test_dir = Path("tests")
    
    if len(sys.argv) > 1:
        # If file paths are provided as arguments, use those
        test_files = [Path(file_path) for file_path in sys.argv[1:]]
    else:
        # Otherwise process all Python files in the tests directory
        test_files = list(test_dir.glob("**/*.py"))
    
    fixed_files = 0
    
    print("Fixing test files...")
    for test_file in test_files:
        if test_file.exists():
            print(f"Processing file: {test_file}")
            with open(test_file, 'r') as f:
                content = f.read()
                if "mock_db" in content:
                    print(f"File contains mock_db references: {test_file}")
            
            if fix_test_file(test_file):
                fixed_files += 1
                print(f"  Fixed test file: {test_file}")
    
    print(f"Fixed {fixed_files} test files")
    print("Test fixture compatibility fixes complete!")


if __name__ == "__main__":
    main()