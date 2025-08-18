# Fish Shell Quick Start Guide

This project includes native support for Fish shell! Here's how to get started:

## Setup

1. **Clone and activate environment:**
   ```fish
   git clone https://github.com/basiphobe/sci-assist.git
   cd sci-assist
   python -m venv .venv
   source .venv/bin/activate.fish
   pip install -e .
   ```

2. **Configure environment:**
   ```fish
   cp .env.example .env
   # Edit .env with your Discord token and LLM settings
   nano .env
   ```

3. **Set up auto-start service:**
   ```fish
   ./setup_service.fish
   ```

## Service Management

Use the fish-specific management script:

```fish
# Start the bot
./bot_control.fish start

# Check status
./bot_control.fish status

# View live logs
./bot_control.fish logs

# Stop the bot
./bot_control.fish stop

# Restart the bot
./bot_control.fish restart

# Enable/disable auto-start
./bot_control.fish enable
./bot_control.fish disable
```

## Fish Shell Benefits

- **Native fish syntax**: Scripts use proper fish conditional statements and loops
- **Better error handling**: Fish-specific error checking
- **Shell detection**: Setup scripts automatically detect fish shell
- **Consistent experience**: All commands work naturally in fish

## Troubleshooting

If you encounter issues with the bash scripts, always use the `.fish` versions:
- Use `setup_service.fish` instead of `setup_service.sh`
- Use `bot_control.fish` instead of `bot_control.sh`

The fish scripts provide the same functionality with proper fish shell compatibility.
