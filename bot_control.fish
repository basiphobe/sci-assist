#!/usr/bin/env fish

# Science Assistant Bot - Service Management Script (Fish Shell)
# Easy commands to manage your bot service

#!/usr/bin/env fish

# SCI-Assist Bot - Service Management Script (Fish Shell)

switch $argv[1]
    case "start"
        echo "🚀 Starting SCI-Assist Bot..."
        sudo systemctl start sci-assist-bot
    case stop
        echo "🛑 Stopping SCI-Assist Bot..."
        sudo systemctl stop sci-assist-bot
    case restart
        echo "🔄 Restarting SCI-Assist Bot..."
        sudo systemctl restart sci-assist-bot
    case status
        echo "📊 Bot Service Status:"
        sudo systemctl status sci-assist-bot
    case logs
        echo "📋 Bot Logs (press Ctrl+C to exit):"
        sudo journalctl -u sci-assist-bot -f
    case enable
        echo "✅ Enabling auto-start on boot..."
        sudo systemctl enable sci-assist-bot
    case disable
        echo "❌ Disabling auto-start on boot..."
        sudo systemctl disable sci-assist-bot
    case '*'
        echo "🤖 SCI-Assist Bot Management (Fish Shell)"
        echo ""
        echo "Usage: $argv[0] {start|stop|restart|status|logs|enable|disable}"
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
end
