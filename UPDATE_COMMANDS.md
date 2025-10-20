# 🔧 Update Bot Commands

## Quick Update

Run this command to update bot commands with the new `/webapp` command:

```bash
python bot/utils/update_commands.py
```

You should see:
```
✅ Bot: @Test_NJ_bot
✅ Commands updated successfully!

📝 Available commands:
  /start - Start the bot
  /webapp - Open web application
  /help - Get help
  /menu - Show main menu
  /balance - Check balance
  /topup - Top up balance
  /history - Transaction history
  /transcribe - Send media for transcription
  /settings - Bot settings
  /support - Contact support
```

## What Changed

Added `/webapp` command to the bot's command list:
- Position: 2nd command (right after `/start`)
- Description: "Open web application"
- Action: Opens inline keyboard with webapp buttons

## Files Modified

1. **`bot/utils/commands.py`**
   - Added `/webapp` to default_commands list

2. **`bot/utils/setup_menu_button.py`**
   - Already had `/webapp` command

3. **`bot/utils/update_commands.py`** *(NEW)*
   - Standalone script to update commands

## How to Use /webapp Command

Users can now type `/webapp` in the bot:
```
User: /webapp

Bot: 🌐 Web Application

Access the full web interface with advanced features:

✨ Features:
• Upload files via drag & drop
• View transcription history
• Manage your balance
• Download transcriptions
• Better mobile experience

[🌐 Open Web App] [📤 Upload File] [📊 View History]
```

## Commands Overview

| Command | Description | Available To |
|---------|-------------|--------------|
| /start | Start the bot | Everyone |
| /webapp | Open web application | Everyone |
| /help | Get help | Everyone |
| /menu | Show main menu | Everyone |
| /balance | Check balance | Everyone |
| /topup | Top up balance | Everyone |
| /history | Transaction history | Everyone |
| /transcribe | Send media | Everyone |
| /settings | Bot settings | Everyone |
| /support | Contact support | Everyone |

## Admin Commands

Admins also get these additional commands:
- /admin - Admin panel
- /stats - Bot statistics
- /broadcast - Send broadcast
- /users - User management

## Testing

1. **Update commands:**
   ```bash
   python bot/utils/update_commands.py
   ```

2. **Check in Telegram:**
   - Open your bot
   - Type `/` to see command list
   - `/webapp` should appear

3. **Test the command:**
   - Send `/webapp`
   - Click "Open Web App" button
   - Should open webapp and auto-login

## Automatic Updates

Commands are automatically set when:
1. Bot starts up (`bot/main.py` calls `set_bot_commands()`)
2. Menu button is configured (`setup_menu_button.py`)
3. Manual update script is run (`update_commands.py`)

## Troubleshooting

### Command not showing?

**Solution 1:** Restart bot
```bash
# Stop bot (Ctrl+C)
python bot/main.py
```

**Solution 2:** Clear Telegram cache
- Telegram Settings → Advanced → Clear Cache
- Restart Telegram app

**Solution 3:** Run update script
```bash
python bot/utils/update_commands.py
```

### Wrong commands showing?

**Check configuration:**
```python
# In bot/utils/commands.py
default_commands = [
    BotCommand(command="webapp", description="Open web application"),
    # ... other commands
]
```

**Re-run update:**
```bash
python bot/utils/update_commands.py
```

## Adding More Commands

To add a new command:

1. **Add to `bot/utils/commands.py`:**
   ```python
   default_commands = [
       # ... existing commands
       BotCommand(command="mycommand", description="My new command"),
   ]
   ```

2. **Create handler in `bot/handlers/`:**
   ```python
   @router.message(Command("mycommand"))
   async def cmd_mycommand(message: Message):
       await message.answer("My command response!")
   ```

3. **Update commands:**
   ```bash
   python bot/utils/update_commands.py
   ```

4. **Restart bot:**
   ```bash
   python bot/main.py
   ```

## Command Best Practices

1. **Keep descriptions short** - Max ~50 characters
2. **Use action verbs** - "Open", "Show", "Check", etc.
3. **Order by importance** - Most used commands first
4. **Group related commands** - Balance, topup, history together
5. **Admin commands separate** - Use BotCommandScopeChat

## Summary

✅ `/webapp` command added to bot
✅ Command list updated
✅ Available in Telegram bot menu
✅ Opens web application interface

**Update commands:** `python bot/utils/update_commands.py`
**Test command:** Type `/webapp` in bot

Done! 🎉
