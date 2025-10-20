# Telegram WebApp Auto-Authentication Guide

## 🎉 What's Been Implemented

Your webapp now supports **automatic authentication** when users open it from Telegram! No more manual login links needed.

## 🔐 How It Works

### Flow:
1. User clicks "Open Web App" button in Telegram bot
2. Telegram opens your webapp with `initData` (encrypted user info)
3. Your webapp automatically:
   - Detects it's opened from Telegram
   - Sends `initData` to backend for validation
   - Validates signature using bot token (HMAC-SHA256)
   - Logs user in automatically
   - Redirects to dashboard

### Security:
- ✅ Cryptographically signed data from Telegram
- ✅ Validated using HMAC-SHA256 with bot token
- ✅ Timestamp verification (max 1 hour old)
- ✅ Automatic user creation for new users
- ✅ User info updates on each login

## 📂 New Files Created

### 1. `django_admin/webapp/telegram_auth.py`
Telegram WebApp authentication utilities:
- `validate_telegram_webapp_data()` - Validates initData signature
- `extract_user_from_init_data()` - Extracts user info
- `create_telegram_auth_response()` - Standardized responses

### 2. Updated Files:
- `webapp/views.py` - Added `telegram_webapp_auth()` endpoint
- `webapp/urls.py` - Added `/api/auth/telegram/` route
- `templates/landing.html` - Added auto-auth JavaScript
- `templates/base.html` - Added Telegram helper functions

## 🚀 Testing

### Step 1: Ensure Bot Token is Set
Check your `.env` file:
```bash
BOT_TOKEN=your_bot_token_here
WEB_APP_URL=https://transcription.avlo.ai
```

### Step 2: Restart Django
```bash
python django_admin/manage.py runserver
```

### Step 3: Test in Telegram
1. Open your bot: @Test_NJ_bot
2. Click menu button (⚡) or send `/webapp`
3. Click "Open Web App"
4. **Should automatically log in and redirect to dashboard!**

## 🔍 What Happens Behind the Scenes

### 1. Telegram WebApp Opens
```javascript
// Landing page detects Telegram WebApp
if (window.Telegram && window.Telegram.WebApp.initData) {
    // Telegram WebApp detected!
}
```

### 2. Frontend Sends initData
```javascript
fetch('/api/auth/telegram/', {
    method: 'POST',
    body: JSON.stringify({
        initData: tg.initData  // Telegram's encrypted data
    })
})
```

### 3. Backend Validates
```python
# Validate signature
validated_data = validate_telegram_webapp_data(init_data, bot_token)

# Extract user info
user_data = extract_user_from_init_data(validated_data)

# Find or create user
user = TelegramUser.objects.get(telegram_id=user_data['telegram_id'])

# Log in
login(request, user)
```

### 4. User Redirected
```javascript
// Success! Go to dashboard
window.location.href = '/dashboard/';
```

## 📱 User Experience

### From Telegram:
1. Click "Open Web App" → **Instant access, no login needed!**
2. Shows "Authenticating..." briefly
3. Redirects to dashboard automatically

### From Browser (not Telegram):
1. Shows landing page
2. "Open Telegram Bot" button
3. Directs to bot for authentication link

## 🔧 API Endpoint

### POST `/api/auth/telegram/`

**Request:**
```json
{
    "initData": "query_id=AAHdF6IQAAAAAN0XohDhrOrc&user=%7B%22id%22%3A279058397..."
}
```

**Success Response:**
```json
{
    "success": true,
    "authenticated": true,
    "message": "Authentication successful",
    "user": {
        "id": 1,
        "telegram_id": 123456789,
        "first_name": "John",
        "username": "johndoe"
    }
}
```

**Error Response:**
```json
{
    "success": false,
    "authenticated": false,
    "message": "Invalid or expired initData"
}
```

## 🛡️ Security Features

### 1. Signature Validation
- Uses HMAC-SHA256 with bot token
- Prevents tampering with user data
- Telegram's standard validation algorithm

### 2. Timestamp Check
- initData expires after 1 hour
- Prevents replay attacks

### 3. User Verification
```python
# Secret key = HMAC_SHA256("WebAppData", bot_token)
secret_key = hmac.new(
    key="WebAppData".encode(),
    msg=bot_token.encode(),
    digestmod=hashlib.sha256
).digest()

# Hash = HMAC_SHA256(secret_key, data_check_string)
calculated_hash = hmac.new(
    key=secret_key,
    msg=data_check_string.encode(),
    digestmod=hashlib.sha256
).hexdigest()
```

## 🎯 Features

### Automatic User Creation
New users are automatically created with:
- Telegram ID
- First name, last name
- Username
- Language code
- Premium status
- Wallet creation

### User Info Updates
Existing users get updated on each login:
- Name changes
- Username changes
- Premium status
- Last login time

### Seamless Integration
- Works with existing token-based auth
- No breaking changes
- Backward compatible

## 🐛 Troubleshooting

### "Invalid or expired initData"
**Cause:** initData validation failed

**Solutions:**
1. Check `BOT_TOKEN` in .env is correct
2. Ensure Django server is running
3. Check browser console for errors
4. Verify WEB_APP_URL matches your domain

### "No initData provided"
**Cause:** Not opened from Telegram WebApp

**Solution:** Use Telegram bot menu button or `/webapp` command

### Authentication loops/redirects
**Cause:** Session not being saved

**Solutions:**
1. Check Django `SECRET_KEY` is set
2. Verify `SESSION_COOKIE_SECURE` settings
3. Clear browser cookies
4. Check Django session middleware is enabled

### User not found after auth
**Cause:** User creation failed

**Solutions:**
1. Check database migrations are run
2. Verify Wallet model auto-creation works
3. Check Django logs for errors

## 📊 Monitoring

### Check Authentication Logs
```bash
# In Django logs, look for:
grep "authenticated via WebApp" logs/django.log
grep "Telegram WebApp auth error" logs/django.log
```

### Debug Mode
Add to your view for debugging:
```python
logger.debug(f"initData: {init_data}")
logger.debug(f"Validated data: {validated_data}")
logger.debug(f"User data: {user_data}")
```

## 🎨 Customization

### Change Auth Timeout
```python
# In telegram_auth.py
validate_telegram_webapp_data(
    init_data,
    bot_token,
    max_age_seconds=7200  # 2 hours instead of 1
)
```

### Add Custom User Fields
```python
# In views.telegram_webapp_auth()
user.custom_field = user_data.get('custom_field')
user.save()
```

### Customize Redirect
```javascript
// In landing.html
if (data.success) {
    window.location.href = '/custom-page/';  // Change redirect
}
```

## ✅ Testing Checklist

- [ ] Django server running
- [ ] BOT_TOKEN set correctly in .env
- [ ] WEB_APP_URL matches your domain
- [ ] Menu button configured (`python bot/utils/setup_menu_button.py`)
- [ ] Bot is running
- [ ] Open webapp from Telegram
- [ ] Auto-authentication works
- [ ] Redirects to dashboard
- [ ] User info is correct
- [ ] Works for new users
- [ ] Works for existing users

## 🔗 References

- [Telegram WebApp Documentation](https://core.telegram.org/bots/webapps)
- [Validating initData](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)

## 💡 Tips

1. **Always use HTTPS in production** - Telegram requires it
2. **Test with different users** - New users and existing users
3. **Check browser console** - Helpful debug info
4. **Monitor Django logs** - Track authentication attempts
5. **Keep bot token secure** - Never expose in frontend

## 🎊 Success!

Your users can now access the webapp instantly from Telegram with automatic authentication! No more copying auth links or manual logins.

**User clicks → Auto-authenticated → Dashboard** 🚀
