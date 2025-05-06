# Shallot Backend Test Plan

This document outlines a comprehensive test plan to achieve 100% test coverage for the Shallot backend.

## Test Coverage Goals

The goal is to achieve 100% test coverage across all modules in the Shallot backend, focusing on:

1. Core functionality
2. API endpoints
3. Command processing
4. Authentication and security
5. Integration with chat platforms
6. Database operations

## Existing Tests

The project currently has tests for:
- `test_main.py`: Basic API health checks
- `test_permissions.py`: Permission system
- `test_validation.py`: Command validation
- `test_escalate.py`: Escalate command functionality
- `test_matrix.py`: Matrix integration

## Test Plan by Module Category

### 1. Core Modules

#### 1.1 Chat Management (`core/chat_manager.py`)
- Test `ChatServiceManager` initialization
- Test service retrieval by platform
- Test message sending functionality
- Test file sending functionality
- Test message formatting
- Test user validation
- Test mocking of external chat services

#### 1.2 Security (`core/security.py`)
- Test password hashing and verification
- Test JWT token creation and validation
- Test token expiration

#### 1.3 Permissions System (`core/permissions.py`, already covered)
- Expand existing tests to cover edge cases

#### 1.4 Platform Services (`core/discord.py`, `core/slack.py`, `core/matrix.py`)
- Test initialization
- Test message sending/formatting using mocks
- Test error handling

#### 1.5 SecurityOnion API (`core/securityonion.py`)
- Test client initialization
- Test connection logic
- Test request formatting
- Test response handling
- Mock external API calls

### 2. API Endpoints

#### 2.1 Authentication (`api/auth.py`)
- Test token endpoint
- Test refresh token
- Test user retrieval from token
- Test setup required check
- Test first user creation

#### 2.2 User Management (`api/users.py`)
- Test user creation
- Test user listing
- Test user updates
- Test user deletion

#### 2.3 Settings Management (`api/settings.py`)
- Test settings retrieval
- Test settings updates

#### 2.4 Health Check (`api/health.py`)
- Test health endpoint response

### 3. Command Modules

#### 3.1 Command Base (`api/commands/core.py`)
- Test command routing
- Test command validation
- Test permission checking

#### 3.2 Alert Commands (`api/commands/alerts.py`)
- Test alert retrieval
- Test response formatting
- Test error handling
- Mock Security Onion API responses

#### 3.3 Other Command Modules
- Test each command processor
- Test argument validation
- Test response formatting

### 4. Services

#### 4.1 Chat Permissions (`services/chat_permissions.py`)
- Test permission checks
- Test role-based access

#### 4.2 Chat Users (`services/chat_users.py`)
- Test user creation
- Test user retrieval
- Test user updates

#### 4.3 Settings Service (`services/settings.py`)
- Test settings retrieval
- Test settings modification

### 5. Database and Models

#### 5.1 Database Operations (`database.py`)
- Test connection
- Test session management

#### 5.2 Models (`models/*.py`)
- Test model validation
- Test relationships
- Test defaults

## Testing Approach

For each module, we will create dedicated test files following these patterns:

1. **Unit Tests**: Testing individual functions and methods in isolation
2. **Integration Tests**: Testing interactions between components
3. **Mocking**: Use mocks for external services (Discord, Slack, Security Onion API)
4. **Fixtures**: Create reusable test fixtures for database and API clients

## Test File Structure

Each test file will be created in the `tests/` directory with the naming convention `test_<module_name>.py`.

## Implementation Order

1. Core modules (security, chat management)
2. API authentication
3. Command modules
4. Services
5. Database operations
6. Integration tests

## Notes on Mocking

- Use `pytest-mock` for function mocks
- Use `pytest-asyncio` for async function testing
- Use `httpx.MockTransport` for mocking HTTP responses

## Test File Creation Plan

1. `test_chat_manager.py`
2. `test_security.py`
3. `test_auth_api.py`
4. `test_users_api.py`
5. `test_settings_api.py`
6. `test_commands_core.py`
7. `test_alerts_command.py`
8. `test_whois_command.py`
9. `test_dig_command.py`
10. `test_hunt_command.py`
11. `test_chat_services.py`
12. `test_securityonion.py`
13. `test_discord.py`
14. `test_slack.py`
15. `test_database.py`
16. `test_models.py`
17. `test_schemas.py`
18. `test_services.py`