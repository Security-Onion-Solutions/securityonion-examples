## Vidalia

A comprehensive security operations web application example that showcases Security Onion's API capabilities. Vidalia demonstrates some of the key uses for external API access for things like PCAP, case management and grid monitoring.

These is just an EXAMPLE and is TOTALLY UNSUPPORTED!

If this breaks anything you get to keep BOTH pieces!

**Core Features:**

Alert Investigation:
- Asynchronous job management for long-running PCAP operations
- Real-time job status tracking and notifications
- Direct PCAP download functionality

Case Management:
- Full incident lifecycle tracking
- Priority and severity classification
- Case status workflow management
- Collaborative commenting system
- Tag-based organization
- Filtering and sorting capabilities

Grid Management:
- Real-time node health monitoring
- System metrics tracking (CPU, memory, disk usage)
- Node uptime monitoring
- Automated reboot management
- Status alerts for node issues

Technical Features:
- RESTful API integration with Security Onion
- Responsive Flask-based web interface
- Comprehensive error handling and logging
- Real-time data updates with cache control
- JSON API endpoints for automation
- Extensive test coverage

**Tech Stack:**
- Python/Flask for backend
- HTML/CSS for frontend
- pytest for testing

**Getting Started:**

Vidalia can be installed either traditionally using Python/pip or using Docker. Choose the installation method that best suits your environment.

### Traditional Installation

1. Clone the repository
2. Navigate to the vidalia directory
3. Copy `.env.example` to `.env` and configure your settings:
   - `SO_CLIENT_ID`: Your Security Onion API client ID (required)
   - `SO_CLIENT_SECRET`: Your Security Onion API client secret (required)
   - `SO_API_URL`: Security Onion API URL (defaults to http://SOMANAGER:443)
   - `SECRET_KEY`: Flask secret key (defaults to dev mode key)
4. Install dependencies: `pip install -r requirements.txt`
5. Start the application: `./start.sh`

### API Client Permissions

You will need to assign permissions to the API key you create. Here is a minimum set od permissions:

Cases: Read  
Clients: Read  
Events: Read  
Grid: Read, Write  
Jobs: Pivot, Process, Read, Write  
Nodes: Read  
Permissions: Read  
Roles: Read  
Users: Read

### Docker Installation

Prerequisites:
- Docker installed and running
- Docker Compose (usually included with Docker Desktop)

1. Clone the repository
2. Navigate to the vidalia directory
3. Run the start script: `./start-docker.sh`

The script will:
- Check for Docker installation
- Prompt for configuration if .env doesn't exist:
  - Security Onion API URL (defaults to https://SOMANAGER:443)
  - Client ID (required)
  - Client Secret (required)
- Prompt for port selection (defaults to 5000)
- Build and start the container

Available Commands:
```bash
./start-docker.sh start   # Build and start container (default command)
./start-docker.sh stop    # Stop and remove container
./start-docker.sh logs    # View container logs
./start-docker.sh config  # Update Security Onion configuration
```

Docker-specific Notes:
- Logs are persisted to the ./logs directory through volume mounting
- The container uses host.docker.internal to connect to Security Onion API
- Container auto-restarts unless explicitly stopped
- Port can be customized during startup
- All environment variables from .env are passed to the container

**Running Tests:**
1. Configure test environment:
   - Copy `.env.example` to `.env.test` for test configuration
   - The test environment uses mock API endpoints by default (https://mock-so-api)
   - Default test credentials are provided in `.env.test`:
     * `SO_API_URL`: Mock API URL for testing
     * `SO_CLIENT_ID`: Test client ID
     * `SO_CLIENT_SECRET`: Test client secret
   - Test configuration can be customized by modifying `.env.test`

2. Make test.sh executable and run tests:
   ```bash
   chmod +x test.sh
   ./test.sh
   ```

The test script will:
- Create a fresh Python virtual environment
- Install all dependencies in the virtual environment
- Load test configuration from `.env.test`
- Run the test suite with mock API endpoints
- Display detailed test results and any failures

Note: You need Python 3 and the venv module installed. If you get a virtual environment
creation error, install the required package for your system:

```bash
# Ubuntu/Debian
sudo apt-get install python3-venv

# Fedora
sudo dnf install python3-venv

# macOS (with Homebrew)
brew install python3
```

## Contributing

Feel free to contribute additional example projects that showcase Security Onion integrations. Each project should:

1. Have clear documentation
2. Include tests
3. Follow best practices for the chosen technology
4. Demonstrate practical use cases for Security Onion integration
