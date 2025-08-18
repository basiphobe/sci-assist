#!/usr/bin/env fish

# Setup script for SCI Assist Bot Daily Messages

set -l SCRIPT_DIR (dirname (realpath (status -f)))
set -l DAILY_SCRIPT "$SCRIPT_DIR/daily_message.fish"
set -l SERVICE_FILE "$SCRIPT_DIR/sci-assist-daily.service"
set -l TIMER_FILE "$SCRIPT_DIR/sci-assist-daily.timer"

echo "Setting up SCI Assist Bot Daily Messages..."

# Make daily message script executable
chmod +x "$DAILY_SCRIPT"
echo "✅ Made daily message script executable"

# Install systemd service and timer
sudo cp "$SERVICE_FILE" /etc/systemd/system/
sudo cp "$TIMER_FILE" /etc/systemd/system/
sudo systemctl daemon-reload
echo "✅ Installed systemd service and timer"

# Enable the timer
sudo systemctl enable sci-assist-daily.timer
echo "✅ Enabled daily message timer"

echo ""
echo "Daily message setup complete!"
echo ""
echo "Commands:"
echo "1. Test the message system:"
echo "   $DAILY_SCRIPT test"
echo ""
echo "2. Post a message manually:"
echo "   $DAILY_SCRIPT post [category]"
echo ""
echo "3. Start the daily timer:"
echo "   sudo systemctl start sci-assist-daily.timer"
echo ""
echo "4. Check timer status:"
echo "   sudo systemctl status sci-assist-daily.timer"
echo "   systemctl list-timers sci-assist-daily.timer"
echo ""
echo "5. View daily message logs:"
echo "   sudo journalctl -u sci-assist-daily.service"
echo "   tail -f /var/log/sci-assist-daily.log"
echo ""
echo "The timer is set to run daily at 9:00 AM."
echo "You can change the time by editing the timer file and reloading systemd."
