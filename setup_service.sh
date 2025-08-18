#!/bin/bash

# Science Assistant Bot - Service Setup Script
# This script sets up the bot to start automatically after reboot

set -e

#!/bin/bash

# SCI-Assist Bot - Service Setup Script
# This script sets up the bot to start automatically after reboot

# Set script directory and change to project root
echo "🤖 Setting up SCI-Assist Bot as a system service..."

# Check if running as root for service installation
if [[ $EUID -eq 0 ]]; then
    echo "❌ Don't run this script as root. Run as your normal user."
    echo "   The script will ask for sudo when needed."
    exit 1
fi

# Get the current directory
BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$BOT_DIR/sci-assist-bot.service"

echo "📁 Bot directory: $BOT_DIR"

# Check if the service file exists
if [[ ! -f "$SERVICE_FILE" ]]; then
    echo "❌ Service file not found: $SERVICE_FILE"
    exit 1
fi

# Check if .env file exists and has bot token
if [[ ! -f "$BOT_DIR/.env" ]]; then
    echo "❌ .env file not found. Please create it first."
    exit 1
fi

if ! grep -q "DISCORD_BOT_TOKEN=" "$BOT_DIR/.env" || grep -q "YOUR_BOT_TOKEN_HERE" "$BOT_DIR/.env"; then
    echo "❌ Bot token not configured in .env file"
    exit 1
fi

echo "✅ Configuration files found"

# Install the bot package in development mode if not already installed
echo "📦 Installing bot package..."
cd "$BOT_DIR"
pip install -e .

# Copy service file to systemd directory
echo "🔧 Installing systemd service..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/

# Reload systemd and enable the service
echo "🔄 Enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable sci-assist-bot.service

echo "✅ Service installed and enabled!"
echo ""
echo "🎮 Service Management Commands:"
echo "   Start:   sudo systemctl start sci-assist-bot"
echo "   Stop:    sudo systemctl stop sci-assist-bot"
echo "   Status:  sudo systemctl status sci-assist-bot"
echo "   Logs:    sudo journalctl -u sci-assist-bot -f"
echo ""
echo "� Easy Management Scripts:"
# Detect user's shell
if [[ "$SHELL" == *"fish"* ]]; then
    echo "   Fish shell: ./bot_control.fish start|stop|restart|status|logs"
else
    echo "   Bash/Zsh:  ./bot_control.sh start|stop|restart|status|logs"
fi
echo ""
echo "�🚀 The bot will now start automatically after reboot!"
echo ""

# Ask if user wants to start the service now
read -p "Start the bot service now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting bot service..."
    sudo systemctl start sci-assist-bot
    sleep 2
    sudo systemctl status sci-assist-bot
fi

echo "✅ Setup complete!"
