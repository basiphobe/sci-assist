# Discord Testing Checklist

## Before Deployment
- [ ] Daily messages tested (`./scripts/daily_message.fish test`)
- [ ] Code syntax validated (`python -m py_compile src/discord_llm_bot/bot/client.py`)
- [ ] Database backed up (`cp bot_conversations.db bot_conversations.db.backup`)

## Deployment
- [ ] Run `./safe_deploy.fish`
- [ ] Monitor logs: `sudo journalctl -u sci-assist-bot -f`

## Discord Testing (in #sci-assist channel)

### Test 1: Context Awareness
1. [ ] User A: Post message "I've been having issues with my wheelchair armrest"
2. [ ] User B: Post message "@sci-assist what can help with armrest problems?"
3. [ ] **Expected**: Bot should reference the armrest issue from User A's message

### Test 2: Non-Response Confirmation
1. [ ] Post message "This is a test message" (NO bot tag)
2. [ ] **Expected**: Bot should NOT respond
3. [ ] Check database: Message should be stored for context

### Test 3: Response Only When Tagged
1. [ ] Post message "@sci-assist hello"
2. [ ] **Expected**: Bot should respond with greeting

### Test 4: Multi-User Context
1. [ ] User A: "Has anyone tried FES therapy?"
2. [ ] User B: "Yeah, I've been doing it for 6 months"
3. [ ] User C: "@sci-assist what should I know about FES therapy?"
4. [ ] **Expected**: Bot should reference the conversation from Users A & B

## Success Criteria
- ✅ Bot reads all messages in #sci-assist for context
- ✅ Bot only responds when tagged (@sci-assist or replies)
- ✅ Bot has context from previous untagged messages
- ✅ No responses to untagged messages
- ✅ Daily messages work without hashtags

## Rollback Triggers
- ❌ Bot responds to untagged messages
- ❌ Bot crashes or stops responding
- ❌ Database errors in logs
- ❌ Bot loses context between messages

## Emergency Rollback
```fish
sudo systemctl stop sci-assist-bot
git revert HEAD  # or git reset --hard HEAD~1
cp bot_conversations.db.backup bot_conversations.db
sudo systemctl start sci-assist-bot
```
