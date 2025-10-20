# Telegram Mini App Integration Guide

This guide explains how to integrate your Django webapp as a Telegram Mini App.

## 📋 Prerequisites

1. Your webapp must be accessible via HTTPS (for production)
2. You need your bot token from @BotFather
3. For local testing, you can use tools like ngrok or localtunnel

## 🚀 Quick Start

### Step 1: Update Environment Variables

Add or update your `.env` file with the webapp URL:

```bash
# For production (use HTTPS!)
WEB_APP_URL=https://your-domain.com

# For local development with ngrok
WEB_APP_URL=https://your-ngrok-id.ngrok.io

# For local testing only (limited functionality)
WEB_APP_URL=http://127.0.0.1:8000
```

### Step 2: Setup Menu Button (Recommended)

Run the setup script to configure the persistent menu button:

```bash
# From the project root directory
python bot/utils/setup_menu_button.py
```

This will:
- Add a "Open Web App" button in the chat input area
- Update bot commands with `/webapp` command
- Display confirmation with your webapp URL

To remove the menu button:
```bash
python bot/utils/setup_menu_button.py --remove
```

### Step 3: Start Your Bot

```bash
# Make sure your bot is running
python bot/main.py
```

### Step 4: Test Integration

1. Open your bot in Telegram
2. You should see:
   - A persistent menu button (⚡) in the chat input
   - New commands: `/webapp`, `/start`, etc.
3. Click the menu button or send `/webapp`
4. The mini app should open!

## 📱 Integration Methods

### Method 1: Menu Button (Recommended)

The menu button appears as a persistent button in the chat input area.

**Pros:**
- Always visible
- One-click access
- Native Telegram feature

**Setup:** Already done via `setup_menu_button.py` script

### Method 2: Inline Keyboard Button

Add webapp buttons to specific messages.

**Example usage:**
```python
from aiogram.types import InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

builder = InlineKeyboardBuilder()
builder.add(InlineKeyboardButton(
    text="🌐 Open Web App",
    web_app=WebAppInfo(url="https://your-domain.com")
))

await message.answer("Click to open:", reply_markup=builder.as_markup())
```

**Already implemented in:** `bot/handlers/webapp.py`

### Method 3: Reply Keyboard Button

Add webapp button to the main keyboard.

**Already implemented in:** `bot/keyboards/main_menu.py`

Users will see a "🌐 Open Web App" button in the main menu.

### Method 4: Bot Commands

Send `/webapp` command to get webapp access.

**Already implemented in:** `bot/handlers/webapp.py`

## 🔧 Available Commands

After integration, these commands are available:

- `/start` - Start the bot
- `/webapp` - Open web application
- `/help` - Show help information
- `/balance` - Check balance
- `/transcribe` - Transcription guide
- `/status` - Bot status
- `/support` - Get support

## 🌐 Local Development with NGROK

For local testing, use ngrok to expose your webapp:

### 1. Install ngrok
```bash
# Download from https://ngrok.com/download
# Or use package manager:
choco install ngrok  # Windows
brew install ngrok   # macOS
```

### 2. Start your Django webapp
```bash
python django_admin/manage.py runserver
```

### 3. Expose with ngrok
```bash
ngrok http 8000
```

### 4. Update .env with ngrok URL
```bash
WEB_APP_URL=https://abc123.ngrok.io
```

### 5. Re-run setup script
```bash
python bot/utils/setup_menu_button.py
```

## 📝 File Structure

New files added for miniapp integration:

```
bot/
├── handlers/
│   └── webapp.py              # WebApp handler (NEW)
├── utils/
│   └── setup_menu_button.py   # Menu button setup script (NEW)
└── keyboards/
    └── main_menu.py           # Updated with webapp button

django_admin/
└── templates/
    └── base.html              # Updated with Telegram WebApp SDK
```

## 🔐 Security Considerations

### 1. Validate Telegram Data

The webapp receives initData from Telegram. You should validate it:

```python
# In your Django views
from django.http import JsonResponse
import hmac
import hashlib

def validate_telegram_webapp_data(init_data, bot_token):
    """Validate data from Telegram WebApp"""
    # Implementation in django_admin/webapp/auth.py
    # Check the Telegram documentation for full implementation
    pass
```

### 2. Use HTTPS in Production

Telegram requires HTTPS for miniapps in production:
- Use Let's Encrypt for free SSL certificates
- Or use services like Cloudflare, Nginx with SSL

### 3. CORS Configuration

Update Django settings if needed:

```python
# django_admin/config/settings/base.py
CORS_ALLOWED_ORIGINS = [
    "https://web.telegram.org",
]
```

## 🎨 Telegram WebApp Features

Your webapp now supports these Telegram features:

### 1. Theme Integration
- Automatically detects Telegram theme (light/dark)
- Uses `var(--tg-theme-*)` CSS variables

### 2. Haptic Feedback
- Light vibration on button clicks
- Implemented in `base.html`

### 3. Back Button
- Native Telegram back button support
- Auto-shows on non-home pages

### 4. Viewport Expansion
- Automatically expands to full height
- Better mobile experience

### 5. Closing Confirmation
- Prevents accidental closure
- User-friendly experience

## 📊 Testing Checklist

- [ ] Bot responds to `/webapp` command
- [ ] Menu button appears in chat input
- [ ] Webapp opens in Telegram browser
- [ ] Mobile responsive design works
- [ ] Theme colors adapt to Telegram theme
- [ ] Back button works correctly
- [ ] Upload functionality works
- [ ] History page displays correctly
- [ ] Authentication works via Telegram

## 🐛 Troubleshooting

### Menu Button Not Showing
```bash
# Re-run setup script
python bot/utils/setup_menu_button.py

# Check bot token in .env
# Restart bot
```

### Webapp Won't Open
- Ensure WEB_APP_URL is HTTPS (for production)
- Check Django is running
- Verify URL is accessible
- Check browser console for errors

### Theme Colors Not Working
- Ensure Telegram WebApp SDK is loaded
- Check browser console for JavaScript errors
- Verify you're using latest base.html template

### Local Testing Issues
- Use ngrok for HTTPS tunnel
- Update WEB_APP_URL in .env
- Re-run setup script after URL changes

## 📚 Additional Resources

- [Telegram WebApp Documentation](https://core.telegram.org/bots/webapps)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Aiogram Documentation](https://docs.aiogram.dev/)

## 💡 Tips

1. **Always use HTTPS in production** - Required by Telegram
2. **Test on mobile devices** - WebApps are primarily mobile
3. **Use Telegram's theme colors** - Better user experience
4. **Implement haptic feedback** - Feels more native
5. **Handle back button** - Improves navigation

## 🎉 You're Done!

Your Telegram Mini App is now integrated! Users can access your webapp directly from Telegram with a seamless experience.

For questions or issues, refer to the Telegram documentation or check the bot logs.
