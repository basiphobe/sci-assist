# SCI-Assist Bot

> **🤖 AI-Generated Project**: This entire repository was created by AI (GitHub Copilot) through conversational guidance. The code, documentation, privacy systems, and architecture were all generated through AI chat interactions with minimal human intervention - demonstrating AI's capability to build complete, production-ready applications.

A specialized Discord bot designed to assist the spinal cord injury (SCI) community. Built with privacy-first principles and powered by self-hosted Large Language Models (LLMs), providing knowledgeable, empathetic support while maintaining strict data privacy controls.

## 🎯 Mission

SCI-Assist provides accessible, 24/7 support for individuals with spinal cord injuries, their families, caregivers, and healthcare professionals. The bot combines clinical knowledge with practical experience to offer guidance on medical, rehabilitation, assistive technology, and daily living topics.

## ✨ Features

- 🤖 **Discord Integration**: Full-featured Discord bot with slash commands
- � **SCI Expertise**: Specialized knowledge in spinal cord injury care, rehabilitation, and adaptive living
- � **Privacy-First**: GDPR-compliant data handling with user consent controls
- 🧠 **LLM Interface**: Self-hosted AI models for complete data sovereignty
- � **Smart Memory**: Context-aware conversations that remember your needs
- 🎯 **Community Focus**: Designed specifically for the SCI community
- 📚 **Evidence-Based**: Responses grounded in medical research and practical experience

## 🛡️ Privacy & Data Protection

- **User Consent Required**: No data stored without explicit user permission
- **Retention Controls**: Configurable data retention periods
- **Data Export**: Full GDPR compliance with data export capabilities
- **Anonymized Training**: Community conversations help improve responses while protecting privacy
- **Local Hosting**: All data remains on your infrastructure

## Quick Start

### Prerequisites

- Python 3.11 or higher
- A Discord bot token (from [Discord Developer Portal](https://discord.com/developers/applications))
- A running LLM with HTTP API
- Compatible with multiple shells: Bash, Zsh, Fish, Windows CMD/PowerShell

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/basiphobe/sci-assist
   cd sci-assist
   ```

2. **Install dependencies**:
   ```bash
   pip install -e .
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize the database**:
   ```bash
   alembic upgrade head
   ```

5. **Run the bot**:
   ```bash
   discord-llm-bot
   ```

## Configuration

Create a `.env` file in the project root with the following variables:

```env
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token_here

# LLM Configuration  
LLM_API_URL=http://localhost:8000/v1/chat/completions
LLM_API_KEY=optional_api_key
LLM_MODEL_NAME=your_model_name

# Database Configuration
DATABASE_URL=sqlite:///./bot_conversations.db

# Logging
LOG_LEVEL=INFO
```

## Development

### Setup Development Environment

1. **Clone and install with dev dependencies**:
   ```bash
   git clone https://github.com/basiphobe/sci-assist
   cd sci-assist
   pip install -e ".[dev]"
   ```

2. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

3. **Run tests**:
   ```bash
   pytest
   ```

4. **Run with coverage**:
   ```bash
   pytest --cov=discord_llm_bot --cov-report=html
   ```

5. **Format code**:
   ```bash
   black src tests
   ruff check src tests --fix
   ```

6. **Type checking**:
   ```bash
   mypy src/discord_llm_bot
   ```

### Project Structure

```
sci-assist-bot/
├── src/discord_llm_bot/           # Main package
│   ├── __init__.py
│   ├── __about__.py               # Version info
│   ├── main.py                    # Entry point
│   ├── config.py                  # Configuration management
│   ├── bot/                       # Discord bot implementation
│   │   ├── __init__.py
│   │   ├── client.py              # Main bot client
│   │   ├── commands.py            # Slash commands
│   │   └── events.py              # Event handlers
│   ├── llm/                       # LLM integration
│   │   ├── __init__.py
│   │   ├── client.py              # LLM API client
│   │   └── models.py              # LLM request/response models
│   ├── database/                  # Database layer
│   │   ├── __init__.py
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── repositories.py       # Data access layer
│   │   └── migrations/            # Alembic migrations
│   ├── conversation/              # Conversation management
│   │   ├── __init__.py
│   │   ├── manager.py             # Conversation logic
│   │   └── memory.py              # Context management
│   └── utils/                     # Utilities
│       ├── __init__.py
│       ├── logging.py             # Logging setup
│       └── exceptions.py          # Custom exceptions
├── tests/                         # Test suite
├── docs/                          # Documentation
├── docker/                        # Docker configuration
├── alembic.ini                    # Database migration config
├── pyproject.toml                 # Project configuration
├── README.md                      # This file
└── .env.example                   # Environment template
```

## Architecture

### Core Components

1. **Discord Bot (`bot/`)**
   - Handles Discord API interactions
   - Processes user messages and commands
   - Manages Discord-specific features (threads, reactions, etc.)

2. **LLM Client (`llm/`)**
   - Interfaces with your self-hosted LLM
   - Handles API requests/responses
   - Manages rate limiting and retries

3. **Conversation Manager (`conversation/`)**
   - Maintains conversation context
   - Manages memory and history
   - Handles conversation threading

4. **Database Layer (`database/`)**
   - Persists conversation history
   - User preferences and settings
   - Repository pattern for clean data access

### Data Flow

```
Discord Message → Bot Event Handler → Conversation Manager → LLM Client → Response → Discord
                                            ↓
                                      Database Storage
```

## Usage

### Basic Commands

- `/chat <message>` - Start or continue a conversation
- `/reset` - Reset conversation history
- `/context` - Show current conversation context
- `/help` - Show available commands

### Advanced Features

- **Reply Threading**: Reply to bot messages to continue conversations
- **Mention Support**: @mention the bot anywhere to start chatting
- **Context Management**: Automatically manages conversation history within token limits
- **Multi-User Support**: Separate conversation histories per user/channel

## Deployment

### Auto-start Service (Linux)

Set up the bot to automatically start on boot using systemd:

```bash
# Choose your shell
./setup_service.sh      # Bash/Zsh users
./setup_service.fish    # Fish shell users
```

**Service Management:**
```bash
# Bash/Zsh users
./bot_control.sh start|stop|restart|status|logs

# Fish shell users  
./bot_control.fish start|stop|restart|status|logs
```

### Docker Deployment

```bash
# Build the image
docker build -t discord-llm-bot .

# Run the container
docker run -d --name discord-bot --env-file .env discord-llm-bot
```

### Production Considerations

- Use PostgreSQL instead of SQLite for better performance
- Set up proper logging aggregation
- Configure health checks and monitoring
- Use secrets management for tokens and API keys

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run the test suite (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/your-username/discord-llm-bot/issues)
- 💬 [Discussions](https://github.com/your-username/discord-llm-bot/discussions)
