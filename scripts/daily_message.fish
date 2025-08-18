#!/usr/bin/env fish

# SCI Assist Bot - Daily Message Poster
# Generates and posts daily engagement messages using LLM

set -g SCRIPT_DIR (dirname (status --current-filename))
set -g PROJECT_ROOT (dirname $SCRIPT_DIR)
set -g PYTHON_SCRIPT "$SCRIPT_DIR/generate_daily_message.py"
set -g CATEGORIES "fact" "tip" "motivation" "tech" "community" "wellness"

function log_message
    set -l message "$argv[1]"
    set -l timestamp (date '+%Y-%m-%d %H:%M:%S')
    # Log to a file in the script directory or stdout if no permissions
    set -l logdir (dirname (status --current-filename))
    set -l logfile "$logdir/daily_message.log"
    
    # Try to write to log file, fall back to stdout
    echo "[$timestamp] $message" >> "$logfile" 2>/dev/null || echo "[$timestamp] $message"
end

function get_python_command
    # Check if we're in a virtual environment
    if test -n "$VIRTUAL_ENV"
        echo "python"
    else if test -f "$PROJECT_ROOT/.venv/bin/python"
        echo "$PROJECT_ROOT/.venv/bin/python"
    else if test -f "$PROJECT_ROOT/venv/bin/python"
        echo "$PROJECT_ROOT/venv/bin/python"
    else
        echo "python3"
    end
end

function generate_llm_message
    set -l category "$argv[1]"
    set -l python_cmd (get_python_command)
    
    log_message "Generating LLM message for category: $category"
    log_message "Using Python command: $python_cmd"
    log_message "Python script path: $PYTHON_SCRIPT"
    
    # Call the Python script to generate the message
    set -l result ($python_cmd "$PYTHON_SCRIPT" "$category" --json 2>&1)
    set -l exit_code $status
    
    log_message "Python script exit code: $exit_code"
    log_message "Python script output: $result"
    
    if test $exit_code -eq 0
        # Extract the JSON part from the end of the output (after all the log lines)
        set -l json_line (echo "$result" | grep -o '{"success": true.*}' | tail -1)
        
        if test -n "$json_line"
            # Parse the extracted JSON
            set -l message (echo "$json_line" | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('message', '')) if data.get('success') else sys.exit(1)" 2>&1)
            set -l parse_code $status
            
            log_message "JSON parse exit code: $parse_code"
            log_message "Extracted JSON: $json_line"
            log_message "Extracted message: $message"
            
            if test $parse_code -eq 0 -a -n "$message"
                echo "$message"
            else
                log_message "Failed to parse extracted JSON: $json_line"
                echo "DEBUG: Failed to parse JSON"
                echo "Extracted JSON: $json_line"
                return 1
            end
        else
            log_message "No JSON found in output: $result"
            echo "DEBUG: No JSON found in output"
            echo "Raw output: $result"
            return 1
        end
    else
        log_message "Python script failed with code $exit_code: $result"
        echo "DEBUG: Python script failed"
        echo "Exit code: $exit_code"
        echo "Output: $result"
        return 1
    end
end

function get_daily_category
    # Rotate through categories based on day of week to ensure variety
    # This creates a predictable but varied schedule
    set -l day_of_week (date +%u)  # 1=Monday, 7=Sunday
    set -l categories_array $CATEGORIES
    
    switch $day_of_week
        case 1  # Monday
            echo "motivation"
        case 2  # Tuesday  
            echo "tip"
        case 3  # Wednesday
            echo "tech"
        case 4  # Thursday
            echo "community"
        case 5  # Friday
            echo "wellness"
        case 6  # Saturday
            echo "fact"
        case 7  # Sunday
            echo "random"  # Keep Sunday as random for variety
    end
end

function post_daily_message
    set -l dry_run false
    set -l category (get_daily_category)  # Auto-select category based on day
    
    # Parse arguments - category can still be overridden
    for arg in $argv
        switch "$arg"
            case "dry-run" "--dry-run"
                set dry_run true
                log_message "Running in dry-run mode - message will not be posted to Discord"
            case "fact" "tip" "motivation" "tech" "community" "wellness" "random"
                set category "$arg"
        end
    end
    
    # Generate message using LLM
    set -l message (generate_llm_message "$category")
    
    if test $status -ne 0 -o -z "$message"
        log_message "Failed to generate message for category: $category"
        return 1
    end
    
    log_message "Generated message: $message"
    
    if test "$dry_run" = "true"
        log_message "DRY RUN: Would post to Discord: $message"
        echo "DRY RUN - Message that would be posted:"
        echo "$message"
        return 0
    end

    # Post the message to Discord using the Python script
    log_message "Posting message to Discord: $message"
    set -l python_cmd (get_python_command)
    
    set -l result ($python_cmd "$PYTHON_SCRIPT" "$category" --post --json 2>&1)
    set -l exit_code $status
    
    if test $exit_code -eq 0
        log_message "Successfully posted daily message to Discord"
        echo "Successfully posted daily message to Discord"
        return 0
    else
        log_message "Failed to post daily message: $result"
        echo "Failed to post daily message: $result"
        return 1
    end
end

function test_categories
    echo "Testing LLM message generation for all categories..."
    echo ""
    
    for category in $CATEGORIES
        echo "=== $category ==="
        set -l message (generate_llm_message "$category")
        if test $status -eq 0
            echo "$message"
        else
            echo "Failed to generate $category message"
        end
        echo ""
    end
end

function preview_message
    set -l category "$argv[1]"
    if test -z "$category"
        set category "random"
    end
    
    echo "=== PREVIEW: What would be posted ==="
    echo "Category: $category"
    echo "Message:"
    echo ""
    
    set -l message (generate_llm_message "$category")
    if test $status -eq 0
        echo "$message"
    else
        echo "Failed to generate message"
        echo ""
        echo "=== DEBUG INFO ==="
        # Show recent log entries
        set -l logdir (dirname (status --current-filename))
        set -l logfile "$logdir/daily_message.log"
        if test -f "$logfile"
            echo "Last few log entries:"
            tail -10 "$logfile"
        else
            echo "No log file found at: $logfile"
        end
    end
    
    echo ""
    echo "=== END PREVIEW ==="
end

# Handle script arguments
switch "$argv[1]"
    case "post"
        set -l category "$argv[2]"
        if test -n "$category"
            post_daily_message "$category"
        else
            post_daily_message
        end
        
    case "dry-run"
        set -l category "$argv[2]"
        if test -n "$category"
            post_daily_message "$category" "dry-run"
        else
            post_daily_message "dry-run"
        end
        
    case "test"
        test_categories
        
    case "preview"
        set -l category "$argv[2]"
        preview_message "$category"
        
    case "list"
        echo "Available categories: $CATEGORIES"
        echo ""
        echo "Usage:"
        echo "  $argv[0] post [category]     - Post a daily message"
        echo "  $argv[0] dry-run [category]  - Preview what would be posted (safe)"
        echo "  $argv[0] preview [category]  - Preview what would be posted without posting (SAFE)"
        echo "  $argv[0] test                - Generate sample messages from all categories"
        echo "  $argv[0] list                - Show this help"
        
    case "*"
        echo "SCI Assist Daily Message Poster (LLM-powered)"
        echo ""
        echo "Usage:"
        echo "  $argv[0] post [category]     - Post a daily message (random category if none specified)"
        echo "  $argv[0] dry-run [category]  - Preview what would be posted without posting (SAFE)"
        echo "  $argv[0] preview [category]  - Preview what would be posted without posting (SAFE)"
        echo "  $argv[0] test                - Generate sample messages from all categories"
        echo "  $argv[0] list                - Show available categories"
        echo ""
        echo "Categories: $CATEGORIES"
        echo ""
        echo "TIP: Use 'dry-run' or 'preview' to safely test before posting!"
end
