# 🚀 Quick Telegram Mini App Setup

## For Production (HTTPS)

### 1. Update .env
```bash
WEB_APP_URL=https://your-domain.com
```

### 2. Run Setup Script
```bash
python bot/utils/setup_menu_button.py
```

### 3. Start Bot
```bash
python bot/main.py
```

### 4. Test
Open your bot → Click menu button (⚡) → Webapp opens!

---

## For Local Development (ngrok)

### 1. Start Django
```bash
python django_admin/manage.py runserver
```

### 2. Start ngrok (in new terminal)
```bash
ngrok http 8000
```

### 3. Copy ngrok URL
Look for: `Forwarding https://abc123.ngrok.io -> http://localhost:8000`

### 4. Update .env
```bash
WEB_APP_URL=https://abc123.ngrok.io
```

### 5. Run Setup Script
```bash
python bot/utils/setup_menu_button.py
```

### 6. Start Bot
```bash
python bot/main.py
```

### 7. Test in Telegram
- Open your bot
- Click menu button or send `/webapp`
- Mini app opens!

---

## 📱 How Users Access

**Option 1:** Menu Button (Recommended)
- Look for ⚡ button next to message input
- Click to open webapp instantly

**Option 2:** Commands
- Send `/webapp` to bot
- Click "Open Web App" button

**Option 3:** Keyboard Button
- Send `/start`
- Click "🌐 Open Web App" button

---

## ✅ Verification

After setup, you should see:
- ✅ Menu button in chat input area
- ✅ `/webapp` command works
- ✅ Webapp opens in Telegram browser
- ✅ Mobile responsive design
- ✅ Telegram theme integration

---

## 🔄 Update WebApp URL

If you change your URL:

```bash
# Update .env with new URL
WEB_APP_URL=https://new-url.com

# Re-run setup
python bot/utils/setup_menu_button.py
```

---

## ❌ Remove Menu Button

```bash
python bot/utils/setup_menu_button.py --remove
```

---

## 📖 Full Guide

See `TELEGRAM_MINIAPP_SETUP.md` for complete documentation.
