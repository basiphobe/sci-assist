#!/usr/bin/env fish

# SCI Assist Bot Watchdog Script
# Monitors bot health and sends alerts when issues are detected

set -g SERVICE_NAME "sci-assist-bot"
set -g LOG_FILE "/var/log/sci-assist-watchdog.log"
set -g CHECK_INTERVAL 300  # 5 minutes
set -g ERROR_THRESHOLD 5  # Alert after 5 consecutive errors

# Load webhook URL from .env file
set -l env_file "/opt/sci-assist/.env"
if test -f $env_file
    set -gx DISCORD_WEBHOOK_URL (grep '^WATCHDOG_DISCORD_WEBHOOK_URL=' $env_file | cut -d '=' -f 2-)
else
    echo "ERROR: .env file not found at $env_file"
    exit 1
end

if test -z "$DISCORD_WEBHOOK_URL"
    echo "ERROR: WATCHDOG_DISCORD_WEBHOOK_URL not set in .env file"
    exit 1
end

# Health check functions
function check_service_status
    systemctl is-active $SERVICE_NAME >/dev/null 2>&1
    return $status
end

function check_recent_errors
    set -l error_count (sudo journalctl -u $SERVICE_NAME --since "5 minutes ago" -p err --no-pager -q 2>/dev/null | wc -l)
    test $error_count -gt 0
    return $status
end

function check_memory_usage
    set -l mem_bytes (systemctl show $SERVICE_NAME --property=MemoryCurrent --value 2>/dev/null)
    # Convert to MB
    set -l mem_mb (math "$mem_bytes / 1024 / 1024")
    test $mem_mb -gt 1000  # Alert if using more than 1GB
    return $status
end

# Logging function
function log_message
    set -l timestamp (date '+%Y-%m-%d %H:%M:%S')
    set -l message "$argv"
    echo "[$timestamp] $message" | sudo tee -a $LOG_FILE
end

# Discord alert function
function send_alert
    set -l title "$argv[1]"
    set -l message "$argv[2]"
    set -l urgency "$argv[3]"  # normal, warning, critical
    
    if test -z "$DISCORD_WEBHOOK_URL"
        log_message "No webhook configured, skipping alert: $title"
        return 1
    end
    
    # Format message based on urgency
    set -l emoji "ℹ️"
    set -l mention ""
    
    switch $urgency
        case critical
            set emoji "🚨"
            set mention "@everyone\n"
        case warning
            set emoji "⚠️"
        case '*'
            set emoji "ℹ️"
    end
    
    # Escape special characters for JSON
    set -l escaped_title (echo -n "$title" | sed 's/"/\\"/g' | sed 's/\\/\\\\/g')
    set -l escaped_message (echo -n "$message" | sed 's/"/\\"/g' | sed 's/\\/\\\\/g' | sed 's/$/\\n/g' | tr -d '\n')
    
    set -l discord_message "$mention$emoji **$escaped_title**\\n$escaped_message"
    
    curl -H "Content-Type: application/json" \
         -X POST \
         -d "{\"content\": \"$discord_message\"}" \
         "$DISCORD_WEBHOOK_URL" >/dev/null 2>&1
    
    if test $status -eq 0
        log_message "Alert sent: $title"
        return 0
    else
        log_message "Failed to send alert: $title"
        return 1
    end
end

# Test webhook function
function test_webhook
    if test -z "$DISCORD_WEBHOOK_URL"
        echo "ERROR: DISCORD_WEBHOOK_URL not set"
        return 1
    end
    
    echo "Testing Discord webhook..."
    send_alert "Watchdog Test" "This is a test message from the SCI Assist Bot watchdog." "normal"
    
    if test $status -eq 0
        echo "✓ Webhook test successful"
        return 0
    else
        echo "✗ Webhook test failed"
        return 1
    end
end

# Get service information for alerts
function get_service_info
    set -l status_info (systemctl show $SERVICE_NAME --property=ActiveState,SubState,MainPID,MemoryCurrent,NRestarts 2>/dev/null)
    set -l uptime (systemctl show $SERVICE_NAME --property=ActiveEnterTimestamp --value 2>/dev/null)
    set -l error_count (sudo journalctl -u $SERVICE_NAME --since "1h" -p warning --no-pager -q 2>/dev/null | wc -l)
    
    echo "Service Status: $status_info"
    echo "Uptime: $uptime"
    echo "Recent Warnings/Errors: $error_count errors in the past hour"
    echo "(Check server logs for details)"
end

# Main monitoring loop
function monitor_service
    set -l consecutive_errors 0
    set -l last_alert_time 0
    set -l alert_cooldown 3600  # 1 hour between repeated alerts
    
    log_message "Starting watchdog for $SERVICE_NAME"
    
    # Initial webhook test
    test_webhook
    
    while true
        set -l current_time (date +%s)
        
        # Check if service is running
        if not check_service_status
            set consecutive_errors (math "$consecutive_errors + 1")
            log_message "Service check failed ($consecutive_errors/$ERROR_THRESHOLD)"
            
            # Send alert if threshold reached and cooldown expired
            if test $consecutive_errors -ge $ERROR_THRESHOLD
                if test (math "$current_time - $last_alert_time") -gt $alert_cooldown
                    set -l service_info (get_service_info)
                    send_alert \
                        "SCI Assist Bot Service Critical" \
                        "The bot service has been down or unresponsive for multiple checks.\\n\\n$service_info" \
                        "critical"
                    set last_alert_time $current_time
                end
            end
        else
            # Service is healthy
            if test $consecutive_errors -gt 0
                log_message "Service recovered after $consecutive_errors failed checks"
                if test $consecutive_errors -ge $ERROR_THRESHOLD
                    send_alert \
                        "SCI Assist Bot Service Recovered" \
                        "The bot service has recovered and is now running normally." \
                        "normal"
                end
                set consecutive_errors 0
            end
        end
        
        # Check for recent errors
        if check_recent_errors
            set -l error_count (sudo journalctl -u $SERVICE_NAME --since "5 minutes ago" -p err --no-pager -q 2>/dev/null | wc -l)
            if test $error_count -gt 3
                log_message "High error rate detected: $error_count errors in past 5 minutes"
                if test (math "$current_time - $last_alert_time") -gt $alert_cooldown
                    send_alert \
                        "SCI Assist Bot High Error Rate" \
                        "Detected $error_count errors in the past 5 minutes. Service may be experiencing issues." \
                        "warning"
                    set last_alert_time $current_time
                end
            end
        end
        
        # Check memory usage
        if check_memory_usage
            set -l mem_bytes (systemctl show $SERVICE_NAME --property=MemoryCurrent --value 2>/dev/null)
            set -l mem_mb (math "$mem_bytes / 1024 / 1024")
            log_message "High memory usage detected: {$mem_mb}MB"
            if test (math "$current_time - $last_alert_time") -gt $alert_cooldown
                send_alert \
                    "SCI Assist Bot High Memory Usage" \
                    "Bot is using {$mem_mb}MB of memory. May indicate a memory leak." \
                    "warning"
                set last_alert_time $current_time
            end
        end
        
        # Wait before next check
        sleep $CHECK_INTERVAL
    end
end

# Handle commands
switch "$argv[1]"
    case run
        monitor_service
    case test
        test_webhook
    case '*'
        echo "Usage: $argv[0] {run|test}"
        echo "  run  - Start monitoring the service"
        echo "  test - Test the Discord webhook"
        exit 1
end
