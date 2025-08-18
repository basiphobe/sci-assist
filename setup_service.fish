#!/usr/bin/env fish

# SCI-Assist Bot - Service Setup Script (Fish Shell)
# This script sets up the bot to start automatically after reboot

echo "🤖 Setting up SCI-Assist Bot as a system service..."

# Check if running as root for service installation
if test (id -u) -eq 0
    echo "❌ Don't run this script as root. Run as your normal user."
    echo "   The script will ask for sudo when needed."
    exit 1
end

# Get the current directory
set BOT_DIR (pwd)
set SERVICE_FILE "$BOT_DIR/sci-assist-bot.service"

echo "📁 Bot directory: $BOT_DIR"

# Check if the service file exists
if not test -f "$SERVICE_FILE"
    echo "❌ Service file not found: $SERVICE_FILE"
    exit 1
end

# Check if .env file exists and has bot token
if not test -f "$BOT_DIR/.env"
    echo "❌ .env file not found. Please create it first."
    exit 1
end

if not grep -q "DISCORD_TOKEN=" "$BOT_DIR/.env"; or grep -q "YOUR_BOT_TOKEN_HERE" "$BOT_DIR/.env"
    echo "❌ Bot token not configured in .env file"
    exit 1
end

echo "✅ Configuration files found"

# Install the bot package in development mode if not already installed
echo "📦 Installing bot package..."
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
echo "📋 Easy Management Script:"
echo "   Fish shell: ./bot_control.fish start|stop|restart|status|logs"
echo ""
echo "🚀 The bot will now start automatically after reboot!"
echo ""

# Ask if user wants to start the service now
echo -n "Start the bot service now? (y/n): "
read -n 1 response
echo ""
if test "$response" = "y"; or test "$response" = "Y"
    echo "🚀 Starting bot service..."
    sudo systemctl start sci-assist-bot
    sleep 2
    sudo systemctl status sci-assist-bot
end

echo "✅ Setup complete!"
