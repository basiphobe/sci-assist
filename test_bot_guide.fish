#!/usr/bin/env fish

# Test Bot Changes - Manual Testing Guide
# This script helps you test the bot changes safely

echo "=== SCI-Assist Bot Testing Guide ==="
echo ""

echo "1. BACKUP FIRST"
echo "   - Current database is at: bot_conversations.db"
echo "   - Copy it before testing: cp bot_conversations.db bot_conversations.db.backup"
echo ""

echo "2. TEST DAILY MESSAGES"
echo "   - Test the improved daily message generation:"
echo "   ./scripts/daily_message.fish preview tip"
echo "   ./scripts/daily_message.fish preview community" 
echo "   ./scripts/daily_message.fish preview wellness"
echo ""
echo "   - Look for:"
echo "     ✓ No hashtags (#)"
echo "     ✓ Questions that invite discussion"
echo "     ✓ Appropriate bot perspective (not claiming personal SCI experience)"
echo ""

echo "3. TEST BOT LOCALLY (SAFE)"
echo "   - Create a test environment variable:"
echo "   echo 'CONVERSATION_SHARED_CONTEXT_CHANNEL_ID=999999999' > .env.test"
echo ""
echo "   - Start bot with test config to check it starts without errors:"
echo "   # This won't affect your live channel since we're using a fake channel ID"
echo ""

echo "4. DEPLOYMENT STEPS"
echo "   - Stop the current bot: sudo systemctl stop sci-assist-bot"
echo "   - Deploy changes: git push (if using git deployment)"
echo "   - Start bot: sudo systemctl start sci-assist-bot"
echo "   - Monitor logs: sudo journalctl -u sci-assist-bot -f"
echo ""

echo "5. VALIDATION AFTER DEPLOYMENT"
echo "   - Send a test message in #sci-assist WITHOUT tagging bot"
echo "   - Send another message that tags the bot"
echo "   - Bot should:"
echo "     ✓ NOT respond to the first message"
echo "     ✓ Respond to the second message"
echo "     ✓ Have context from the first message in its response"
echo ""

echo "6. ROLLBACK PLAN"
echo "   - If issues occur:"
echo "   - git revert [commit-hash] (if using git)"
echo "   - Or restore backup: cp bot_conversations.db.backup bot_conversations.db"
echo "   - Restart: sudo systemctl restart sci-assist-bot"
echo ""

echo "Ready to test? Start with daily messages:"
echo "./scripts/daily_message.fish preview tip"
