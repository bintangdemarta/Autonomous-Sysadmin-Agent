# Autonomous Sysadmin Agent (Nexus-CLI)

A deterministic SSH automation tool that translates natural language commands into server commands using rule-based logic instead of AI/LLM.

## Overview

The Autonomous Sysadmin Agent (Nexus-CLI) is designed to simplify server administration by allowing users to execute server commands using natural language. Rather than relying on complex AI models, this tool uses deterministic rule-based mapping to convert phrases like "cek ram" into "free -h" and execute them securely on remote servers via SSH.

## Features

- **Natural Language Processing**: Convert everyday language to server commands
- **Secure SSH Connections**: Execute commands on remote servers safely
- **Configurable Commands**: Define custom command mappings via JSON
- **Safety Mechanisms**: Confirmation prompts for destructive operations
- **Web Interface**: Easy-to-use dashboard for command execution
- **Dynamic Arguments**: Support for variable inputs using regex patterns

## Installation

### Prerequisites
- Python 3.9+
- Docker and Docker Compose (optional)

### Quick Setup

#### Using Docker (Recommended)
```bash
# Clone the repository
git clone https://github.com/bintangdemarta/Autonomous-Sysadmin-Agent.git
cd Autonomous-Sysadmin-Agent

# Copy environment file
cp .env.example .env

# Edit .env with your server credentials and optional web auth
nano .env

# Build and run
docker-compose build
docker-compose run --rm nexus-cli
```

#### Direct Python Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your server credentials

# Run the application
python main_app.py
```

#### Web Interface
```bash
# Navigate to web directory
cd web

# Install web dependencies
pip install -r requirements.txt

# Run the web server
python app.py
```

## Usage

### Command-Line Interface
```bash
# Interactive mode
python main_app.py

# Single command mode
python main_app.py --command "cek ram"
```

### Web Interface
1. Start the web server: `python app.py`
2. Open browser to `http://localhost:5000`
3. Enter commands in natural language
4. View results and command history

## Configuration

The system uses `config/commands.json` to define command mappings:

```json
{
  "monitoring": [
    {
      "keywords": ["cek ram", "lihat memori", "memory status"],
      "command": "free -h",
      "description": "Display server RAM status"
    },
    {
      "pattern": "hidupkan vm (\\d+)",
      "command": "qm start {0}",
      "description": "Start Proxmox Virtual Machine by ID"
    }
  ]
}
```

## Security Features

- Human-in-the-loop validation for dangerous commands
- Secure SSH connections using Paramiko
- Environment-based credential management with no committed default secrets
- Optional HTTP Basic Auth for the Flask dashboard via `NEXUS_WEB_USERNAME` and `NEXUS_WEB_PASSWORD`
- Persistent JSONL audit logging for executions
- Configurable safety checks


## Runtime Configuration

Copy `.env.example` to `.env` and configure these variables before connecting to real infrastructure:

```env
NEXUS_SSH_HOST=your-server.example.com
NEXUS_SSH_PORT=22
NEXUS_SSH_USER=your-ssh-user
NEXUS_SSH_PASSWORD=
NEXUS_SSH_KEY_PATH=/home/you/.ssh/id_ed25519
NEXUS_WEB_USERNAME=admin
NEXUS_WEB_PASSWORD=change-me
```

Commands marked with `requires_confirmation: true` must be explicitly confirmed using `--yes` in the CLI or `confirmed: true` in the web API payload.

## Extending Functionality

### Adding New Commands
1. Edit `config/commands.json`
2. Add new keyword mappings or regex patterns
3. Restart the application to load changes

## Project Structure

```
├── main_app.py          # Main CLI application
├── nexus/              # Shared parser, safety, SSH, config, and audit modules
├── config/
│   └── commands.json    # Command mappings
├── web/
│   ├── app.py          # Web application
│   ├── templates/      # HTML templates
│   └── static/         # CSS, JS files
├── docker-compose.yml  # Docker configuration
├── requirements.txt    # Python dependencies
└── README.md
```

## Roadmap

- Multi-server support
- Web dashboard with monitoring graphs
- Telegram bot integration
- Advanced scheduling capabilities

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue on the GitHub repository.