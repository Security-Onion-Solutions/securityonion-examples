# Security Onion Examples

This repository contains example projects and integrations for Security Onion, demonstrating different ways to extend and interact with Security Onion's API. 

These are just EXAMPLES and are TOTALLY UNSUPPORTED and not intended for production use!

If this breaks anything you get to keep BOTH pieces!


## Projects

### Vidalia

A comprehensive security operations web application example that showcases Security Onion's API capabilities. Vidalia demonstrates some of the key uses for external API access for things like PCAP, case management and grid monitoring.

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

### Shallot

A chat integration system for Security Onion that enables teams to interact with their security monitoring system through various chat platforms including Matrix, Slack, and Discord.

**Core Features:**

Multi-Platform Support:
- Matrix (unencrypted)
- Slack
- Discord
- Platform-agnostic command handling

Command System:
- Prefix-based command recognition
- Asynchronous command processing
- Platform-agnostic command handling
- Customizable command prefix

Alert System:
- Configurable alert notifications
- Dedicated alert rooms
- Formatted alert messages
- Real-time delivery

Security Features:
- Platform-specific authentication
- API access control
- User permission management
- Secure token storage

**Tech Stack:**
- Python FastAPI backend
- Vue.js frontend
- Matrix/Slack/Discord APIs
- Docker containerization

## License

This repository and its contents are open source. See individual project directories for specific license information.
