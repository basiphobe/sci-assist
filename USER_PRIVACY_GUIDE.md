# 🔒 Privacy & Data Management for SCI-Assist Users

## 📋 Quick Overview

The SCI-Assist bot now has **privacy-first design** - your conversations are **NOT stored** unless you explicitly consent. The bot still helps you, but respects your data privacy.

## 🎯 Key Points

- **Default**: No data storage (privacy-first)
- **Bot Still Works**: Responds to questions without storing conversations
- **Your Choice**: Opt-in to data storage for better conversation context
- **Full Control**: Change your preferences anytime

## 🤖 How to Manage Your Privacy

### 1. **Main Privacy Command**
```
/privacy
```
This opens your personal privacy dashboard where you can:
- See your current consent status
- Learn about data retention policies
- Manage your preferences with interactive buttons

### 2. **Data Export**
```
/data_export
```
Request a copy of all your stored data (GDPR compliance)

### 3. **Data Deletion**
```
/delete_data
```
Request permanent deletion of your data

## ⚙️ Privacy Options Explained

### 🗄️ **Data Retention Consent**
**What it means**: Allow the bot to store your conversations for up to 7 days

**Benefits**:
- ✅ Bot remembers conversation context
- ✅ Better responses in ongoing discussions
- ✅ More natural conversation flow

**Without consent**:
- ❌ No conversation memory between messages
- ✅ Bot still responds and helps
- ✅ Maximum privacy protection

### 📚 **Training Data Consent**
**What it means**: Allow anonymized use of conversations to improve the bot

**Benefits**:
- ✅ Helps make the bot better for everyone
- ✅ Your data is fully anonymized (no personal info)
- ✅ Only conversation patterns used, not personal details

**How anonymization works**:
- Usernames → anonymous IDs (e.g., `user_abc123`)
- Personal info removed (emails, phones, etc.)
- Discord mentions replaced with placeholders
- No way to trace back to you

## 🛡️ Privacy Guarantees

### ✅ **What We Promise**
- **Privacy by Default**: No storage without your consent
- **Transparent Processing**: Clear information about data use
- **Your Control**: Change preferences anytime
- **Automatic Cleanup**: Old data deleted automatically
- **No Third Parties**: Data stays on our secure servers
- **Full Anonymization**: Training data has no personal identifiers

### ❌ **What We DON'T Do**
- Store data without permission
- Share data with third parties
- Use personal info in training data
- Keep data longer than stated
- Track you across other platforms

## 📊 Data Retention Policy

| Data Type | Retention Period | Purpose |
|-----------|------------------|---------|
| **Operational Data** | 7 days | Conversation context |
| **Training Data** | With consent only | Bot improvements |
| **Consent Records** | Until revoked | Privacy management |

## 🔄 How to Use the Privacy System

### **First Time Setup**
1. Use `/privacy` command
2. Read the privacy information
3. Choose your preferences:
   - **Conservative**: No consent (maximum privacy)
   - **Balanced**: Data retention consent only
   - **Supportive**: Both data retention and training consent

### **Changing Your Mind**
- Use `/privacy` anytime to update preferences
- Changes take effect immediately
- Can revoke consent with one click

### **Getting Help**
- Use `/privacy` and click "ℹ️ Learn More" for detailed info
- Ask questions in the server - mods can help
- Bot works the same regardless of your privacy choices

## 🎨 Privacy Dashboard Features

When you use `/privacy`, you'll see:

### 📊 **Current Status Display**
- Your consent status (✅/❌/❓)
- Last update date
- Clear explanations

### 🎛️ **Interactive Buttons**
- **✅ Consent to Data Storage** - Allow conversation storage
- **📚 Consent to Training Use** - Help improve the bot
- **❌ Revoke All Consent** - Maximum privacy mode
- **ℹ️ Learn More** - Detailed privacy information

### 📋 **Policy Information**
- Retention periods
- What data is collected
- How it's used
- Your rights

## 💡 Recommendations

### **For Most Users**:
Consider **data retention consent** if you:
- Have ongoing conversations with the bot
- Want the bot to remember context
- Are comfortable with 7-day storage

### **For Privacy-Focused Users**:
No consent needed if you:
- Want maximum privacy
- Only ask occasional questions
- Don't need conversation context

### **For Supporters**:
Consider **training consent** if you:
- Want to help improve the bot
- Are comfortable with anonymized data use
- Trust the anonymization process

## ❓ Frequently Asked Questions

**Q: Will the bot stop working if I don't consent?**
A: No! The bot responds normally, just without storing conversation history.

**Q: Can I see what data is stored about me?**
A: Yes, use `/data_export` to get a copy of all your data.

**Q: How do I know my data is really anonymized?**
A: The anonymization process is documented and uses cryptographic hashing for user IDs.

**Q: Can I consent to one thing but not the other?**
A: Absolutely! Data retention and training consent are completely separate.

**Q: What happens to old data if I revoke consent?**
A: It gets cleaned up according to the retention policy (within 7 days).

**Q: Can server moderators see my privacy choices?**
A: No, your privacy preferences are private to you and the bot.

---

## 🚀 Get Started

Ready to set your privacy preferences? Use `/privacy` in any channel where the bot is present!

*This system ensures your privacy while still allowing you to get help from SCI-Assist. Your data, your choice!*
