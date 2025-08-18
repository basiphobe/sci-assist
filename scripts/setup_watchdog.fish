#!/usr/bin/env fish

# Setup script for SCI Assist Bot Watchdog

set -l SCRIPT_DIR (dirname (realpath (status -f)))
set -l WATCHDOG_SCRIPT "$SCRIPT_DIR/watchdog.fish"
set -l SERVICE_FILE "$SCRIPT_DIR/sci-assist-watchdog.service"

echo "Setting up SCI Assist Bot Watchdog..."

# Make watchdog script executable
chmod +x "$WATCHDOG_SCRIPT"
echo "✅ Made watchdog script executable"

# Install systemd service
sudo cp "$SERVICE_FILE" /etc/systemd/system/
sudo systemctl daemon-reload
echo "✅ Installed systemd service"

# Enable the service
sudo systemctl enable sci-assist-watchdog
echo "✅ Enabled watchdog service"

echo ""
echo "Watchdog setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit the watchdog script to configure alerts:"
echo "   nano $WATCHDOG_SCRIPT"
echo "   - Set ALERT_EMAIL for email notifications"
echo "   - Set DISCORD_WEBHOOK_URL for Discord notifications"
echo ""
echo "2. Test the watchdog:"
echo "   $WATCHDOG_SCRIPT test"
echo ""
echo "3. Start the watchdog service:"
echo "   sudo systemctl start sci-assist-watchdog"
echo ""
echo "4. Check watchdog status:"
echo "   sudo systemctl status sci-assist-watchdog"
echo ""
echo "5. View watchdog logs:"
echo "   sudo journalctl -u sci-assist-watchdog -f"
echo "   tail -f /var/log/sci-assist-watchdog.log"
