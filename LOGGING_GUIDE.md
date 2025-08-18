# Logging Guide for Discord LLM Bot

This guide explains how to use the comprehensive logging system to monitor and debug your Discord LLM bot.

## Overview

The bot includes advanced logging that tracks:
- **Discord API calls** and events
- **LLM API requests** and responses with timing
- **Database operations** and performance
- **Conversation flow** and context management
- **Error tracking** with correlation IDs
- **Performance metrics** for optimization

## Log Levels

### Development Logging (DEBUG)
```bash
LOG_LEVEL=DEBUG
LOG_FORMAT=rich
```
**What you'll see:**
- Every HTTP request/response to Discord and LLM APIs
- Database queries and their execution times
- Token usage and context window management
- Function entry/exit with parameters
- Request correlation IDs for tracing

### Production Logging (INFO)
```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
```
**What you'll see:**
- User interactions and bot responses
- API call summaries with timing
- Conversation events and state changes
- Error conditions with context
- Performance metrics

### Error-Only Logging (ERROR)
```bash
LOG_LEVEL=ERROR
LOG_FORMAT=json
```
**What you'll see:**
- Only errors and critical issues
- API failures and timeouts
- Database connection problems
- Bot startup/shutdown issues

## Log Formats

### Rich Format (Development)
- **Colorized output** for easy reading
- **Structured display** with proper indentation
- **Traceback highlighting** for errors
- **Time stamps** and **log levels**

### JSON Format (Production)
- **Machine-readable** structured logs
- **Correlation IDs** for request tracing
- **Standardized fields** for log aggregation
- **Compatible** with log management systems

## Understanding Your Logs

### Discord Events
```
service.discord | Discord event: message_received | user_id=123456789 channel_id=987654321
```

### LLM API Calls
```
service.llm | HTTP request initiated | method=POST host=localhost:11434 correlation_id=abc12345
service.llm | LLM interaction completed | model=merged-sci-model total_tokens=150 response_time_ms=1250.5
```

### Conversation Flow
```
service.conversation | Conversation event: context_prepared | conversation_id=1 total_tokens=75 context_usage=75/8192
service.conversation | Starting generate_response | operation=generate_response correlation_id=def67890
```

### Performance Timing
```
Completed handle_conversation_message | operation=handle_conversation_message duration_ms=2105.3 status=success
```

## Monitoring Your Bot

### Key Metrics to Watch

1. **Response Times**
   - `llm_generate_completion` duration
   - `handle_conversation_message` total time
   - HTTP response times

2. **Token Usage**
   - `total_tokens` per request
   - `context_usage` vs. window size
   - Token efficiency trends

3. **Error Rates**
   - Failed LLM API calls
   - Discord API errors
   - Database connection issues

4. **User Activity**
   - Messages processed per hour
   - Unique users and channels
   - Conversation lengths

### Log Analysis Commands

**View real-time logs:**
```fish
# Fish shell
./bot_control.fish logs

# Bash/Zsh  
./bot_control.sh logs
```

**Search for specific events:**
```bash
# Find all LLM API calls
sudo journalctl -u sci-assist-bot | grep "service.llm"

# Find errors only
sudo journalctl -u sci-assist-bot -p err

# Follow logs with correlation ID
sudo journalctl -u sci-assist-bot -f | grep "abc12345"
```

**Performance analysis:**
```bash
# Find slow responses (>5 seconds)
sudo journalctl -u sci-assist-bot | grep "duration_ms" | grep -E "[5-9][0-9]{3}\.[0-9]|[0-9]{5,}\.[0-9]"

# Token usage patterns
sudo journalctl -u sci-assist-bot | grep "total_tokens"

# API error summary
sudo journalctl -u sci-assist-bot | grep "HTTP.*error"
```

## Troubleshooting Common Issues

### High Response Times
**Look for:**
- `response_time_ms > 5000` in LLM calls
- Database query slowdowns
- Network timeout patterns

**Example log entry:**
```
service.llm | HTTP response received | status_code=200 response_time_ms=8542.1 correlation_id=xyz789
```

### Token Limit Issues
**Look for:**
- `context_usage` approaching window size
- Truncation strategies being applied
- Conversation history limits

**Example log entry:**
```
service.conversation | Applied truncation strategy | original_count=25 final_count=15 context_usage=7890/8192
```

### API Failures
**Look for:**
- `status_code >= 400` in HTTP responses
- Connection timeouts
- Authentication errors

**Example log entry:**
```
service.llm | HTTP request failed | status_code=503 error="Service temporarily unavailable"
```

### Discord Issues
**Look for:**
- Discord API rate limiting
- Permission errors
- Command sync failures

**Example log entry:**
```
service.discord | Discord event: rate_limited | retry_after=30.5 endpoint="/channels/123/messages"
```

## Log Rotation and Storage

### Systemd Journal
By default, logs go to the systemd journal:
- **Automatic rotation** based on system settings
- **Compressed storage** for older entries
- **Persistent across reboots**

### File-based Logging (Optional)
For dedicated log files, modify your service:

```ini
# In sci-assist-bot.service
StandardOutput=append:/var/log/sci-assist-bot/bot.log
StandardError=append:/var/log/sci-assist-bot/bot.error.log
```

### Log Aggregation (Production)
For production deployments:
- Use **structured JSON logging**
- Configure **log forwarding** to centralized systems
- Set up **alerting** on error patterns
- Implement **log retention policies**

## Best Practices

1. **Use correlation IDs** to trace request flows
2. **Monitor response times** for performance issues
3. **Set up alerts** for error rate spikes
4. **Regular log analysis** for optimization opportunities
5. **Adjust log levels** based on environment needs

## Sample Log Analysis Scripts

### Error Rate Calculator
```bash
#!/bin/bash
# Calculate error rate over last hour
TOTAL=$(sudo journalctl -u sci-assist-bot --since="1 hour ago" | grep "HTTP.*response" | wc -l)
ERRORS=$(sudo journalctl -u sci-assist-bot --since="1 hour ago" | grep "HTTP.*response.*status_code=[45]" | wc -l)
echo "Error rate: $((ERRORS * 100 / TOTAL))% ($ERRORS/$TOTAL)"
```

### Performance Summary
```bash
#!/bin/bash
# Average response times
sudo journalctl -u sci-assist-bot --since="1 hour ago" | \
grep "duration_ms" | \
grep -o "duration_ms=[0-9]*\.[0-9]*" | \
cut -d= -f2 | \
awk '{sum+=$1; count++} END {printf "Average response time: %.2fms\n", sum/count}'
```

This comprehensive logging system gives you full visibility into your bot's operation, helping you maintain optimal performance and quickly diagnose issues.
