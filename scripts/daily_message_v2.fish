#!/usr/bin/env fish

# SCI Assist Bot - Bot-Mediated Daily Message Poster
# This version ensures messages ONLY post when the bot is running and healthy
# All messages go through the bot's internal API for proper context handling

set -g SCRIPT_DIR (dirname (status --current-filename))
set -g PROJECT_ROOT (dirname $SCRIPT_DIR)
set -g PYTHON_SCRIPT "$SCRIPT_DIR/generate_daily_message_v2.py"
set -g CATEGORIES "fact" "tip" "motivation" "tech" "community" "wellness"

function log_message
    set -l message "$argv[1]"
    set -l timestamp (date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $message"
end

function get_python_command
    # Check if we're in a virtual environment
    if test -n "$VIRTUAL_ENV"
        echo "python"
    else if test -f "$PROJECT_ROOT/.venv/bin/python"
        echo "$PROJECT_ROOT/.venv/bin/python"
    else
        echo "python3"
    end
end

function post_daily_message
    set -l category "$argv[1]"
    set -l dry_run false
    
    # Parse arguments
    for arg in $argv[2..]
        switch "$arg"
            case "dry-run" "--dry-run"
                set dry_run true
                log_message "Running in dry-run mode - will test bot communication but not post"
        end
    end
    
    # Set up command arguments
    set -l cmd_args "$category" "--post"
    if test "$dry_run" = "true"
        set cmd_args $cmd_args "--test"
    end
    
    # Get python command
    set -l python_cmd (get_python_command)
    
    log_message "Using bot-mediated posting system (ensures bot is running)"
    log_message "Generating and posting daily message for category: $category"
    
    # Execute the bot-mediated daily message script
    $python_cmd "$PYTHON_SCRIPT" $cmd_args
    set -l exit_code $status
    
    if test $exit_code -eq 0
        if test "$dry_run" = "true"
            log_message "✅ Dry run completed successfully - bot confirmed it would post the message"
        else
            log_message "✅ Daily message posted successfully through bot"
        end
        return 0
    else
        log_message "❌ Failed to post daily message (exit code: $exit_code)"
        log_message "This could mean:"
        log_message "  - Bot is not running or crashed"
        log_message "  - Bot API is not responding"
        log_message "  - Network connectivity issues"
        log_message "Daily message posting aborted - this ensures messages only happen when bot is healthy"
        return 1
    end
end

function show_help
    echo "SCI Assist Bot - Bot-Mediated Daily Message Poster"
    echo ""
    echo "This script ensures daily messages ONLY post when the bot is running and healthy."
    echo "If the bot crashes or is down, no messages will be posted."
    echo ""
    echo "Usage:"
    echo "  $argv[0] <category> [options]"
    echo ""
    echo "Categories:"
    for category in $CATEGORIES
        echo "  $category"
    end
    echo "  random"
    echo ""
    echo "Options:"
    echo "  dry-run, --dry-run    Test mode - check bot communication but don't post"
    echo ""
    echo "Examples:"
    echo "  $argv[0] motivation           # Post a motivation message through bot"
    echo "  $argv[0] tech dry-run         # Test tech message posting (no actual post)"
    echo ""
    echo "Key Features:"
    echo "  ✅ Bot-mediated posting - all messages go through bot's API"
    echo "  ✅ Health checking - only posts when bot is running and healthy"
    echo "  ✅ Automatic context storage - bot handles message storage and context"
    echo "  ✅ Fail-safe design - no accidental posts when bot is down"
end

# Main script logic
if test (count $argv) -eq 0
    show_help
    exit 1
end

set -l category "$argv[1]"

# Handle help requests
switch "$category"
    case "help" "--help" "-h"
        show_help
        exit 0
end

# Validate category
set -l valid_category false
for valid in $CATEGORIES "random"
    if test "$category" = "$valid"
        set valid_category true
        break
    end
end

if test "$valid_category" = "false"
    log_message "❌ Invalid category: $category"
    echo ""
    show_help
    exit 1
end

# Post the daily message
post_daily_message $argv
