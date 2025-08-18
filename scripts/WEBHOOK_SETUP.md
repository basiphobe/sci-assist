# Discord Webhook Setup for Watchdog Alerts

## Step 1: Create a Discord Webhook

1. **Go to your Discord server**
2. **Right-click the server name** → Server Settings
3. **Go to Integrations** → Webhooks
4. **Click "Create Webhook"**
5. **Configure the webhook:**
   - Name: `SCI Assist Bot Alerts`
   - Channel: `#bot-alerts` (create this channel if needed)
   - Avatar: Optional (you can upload a warning icon)
6. **Copy the Webhook URL** (it looks like: `https://discord.com/api/webhooks/1234567890/abcdef123456789`)

## Step 2: Configure the Watchdog Script

1. **Edit the watchdog script:**
   ```bash
   nano /opt/sci-assist/scripts/watchdog.fish
   ```

2. **Find this line:**
   ```fish
   set -l DISCORD_WEBHOOK_URL ""  # REQUIRED: Discord webhook URL for alerts
   ```

3. **Replace with your webhook URL:**
   ```fish
   set -l DISCORD_WEBHOOK_URL "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_HERE"
   ```

## Step 3: Test the Webhook

```bash
# Test the watchdog (includes webhook test)
/opt/sci-assist/scripts/watchdog.fish test
```

You should see a test message appear in your Discord channel.

## Alert Types

The watchdog will send different types of alerts:

- **ℹ️ Normal:** Test messages, service recovery
- **⚠️ Warning:** Service restarted automatically  
- **🚨 Critical:** Service failed to restart, manual intervention needed

## Example Alert Messages

```
⚠️ **SCI Assist Bot Restarted**
The bot service was automatically restarted due to health check failure.

Time: 2025-08-13 20:15:30
Server: your-server-name
```

```
🚨 **SCI Assist Bot CRITICAL FAILURE**
The bot service has failed and cannot be restarted automatically.

Service Info:
ActiveState=failed
MainPID=0
...

Time: 2025-08-13 20:20:30
Server: your-server-name
```
