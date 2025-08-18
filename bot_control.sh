#!/bin/bash

# SCI-Assist Bot - Service Management Script
# Easy commands to manage your bot service

case "$1" in
    start)
        echo "🚀 Starting Science Assistant Bot..."
        sudo systemctl start sci-assist-bot
        ;;
    stop)
        echo "🛑 Stopping Science Assistant Bot..."
        sudo systemctl stop sci-assist-bot
        ;;
    restart)
        echo "🔄 Restarting Science Assistant Bot..."
        sudo systemctl restart sci-assist-bot
        ;;
    status)
        echo "📊 Bot Service Status:"
        sudo systemctl status sci-assist-bot
        ;;
    logs)
        echo "📋 Bot Logs (press Ctrl+C to exit):"
        sudo journalctl -u sci-assist-bot -f
        ;;
    enable)
        echo "✅ Enabling auto-start on boot..."
        sudo systemctl enable sci-assist-bot
        ;;
    disable)
        echo "❌ Disabling auto-start on boot..."
        sudo systemctl disable sci-assist-bot
        ;;
    *)
        echo "🤖 Science Assistant Bot Management"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|enable|disable}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the bot"
        echo "  stop     - Stop the bot"
        echo "  restart  - Restart the bot"
        echo "  status   - Show bot status"
        echo "  logs     - Show live bot logs"
        echo "  enable   - Enable auto-start on boot"
        echo "  disable  - Disable auto-start on boot"
        exit 1
        ;;
esac
