# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Test Commands

### Shallot
- **Backend**: `cd shallot/backend && poetry install && poetry run pytest` (Python)
- **Backend (single test)**: `cd shallot/backend && poetry run pytest tests/test_file.py::test_function -v`
- **Frontend**: `cd shallot/frontend && npm install && npm run dev` (Vue/TS)
- **Lint (backend)**: `cd shallot/backend && poetry run black src/ && poetry run mypy src/`
- **Type check (frontend)**: `cd shallot/frontend && vue-tsc -b`

### Vidalia
- **Run**: `cd vidalia && pip install -r requirements.txt && ./start.sh`
- **Tests**: `cd vidalia && ./test.sh` or `pytest tests/test_file.py::test_function -v`

## Code Style Guidelines

- **Python**: Black formatter (88 char line length), mypy static typing
- **TypeScript**: strict type checking, Vue single-file components
- **Imports**: Group by standard/third-party/local, alphabetize within groups
- **Naming**: 
  - Python: snake_case for functions/variables, PascalCase for classes
  - TypeScript: camelCase for functions/variables, PascalCase for components
- **Error handling**: Use specific exceptions, log before re-raising
- **Documentation**: Include docstrings for public functions
- **Testing**: Use pytest for Python, mock external dependencies