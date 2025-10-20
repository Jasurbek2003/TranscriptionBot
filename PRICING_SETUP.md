# 🚀 Quick Pricing Setup

## Current Prices
- 🎵 Audio: **500 sum/min**
- 🎬 Video: **600 sum/min**

## Setup (3 Steps)

### Step 1: Create Default Pricing Plan

```bash
python django_admin/scripts/create_default_pricing.py
```

Expected output:
```
✅ Created default pricing plan!
  Name: Standard Plan
  Audio: 500 sum/min
  Video: 600 sum/min
  Status: Active
  Default: Yes
```

### Step 2: Access Django Admin

1. Start Django server (if not running):
   ```bash
   python django_admin/manage.py runserver
   ```

2. Go to: `http://localhost:8000/admin/`

3. Login with superuser credentials

4. Navigate to: **Pricing Plans**

### Step 3: Verify Prices

You should see:
| Name | Audio Price | Video Price | Status | Default |
|------|-------------|-------------|--------|---------|
| Standard Plan | 500 sum/min | 600 sum/min | ACTIVE | ✓ |

**Done!** ✨

## Change Prices Later

1. Go to admin: `http://localhost:8000/admin/pricing/pricingplan/`
2. Click on **Standard Plan**
3. Update prices
4. Click **Save**

**Takes effect immediately!** No restart needed.

## Files Changed

### New Files:
- `apps/pricing/utils.py` - Pricing utilities
- `scripts/create_default_pricing.py` - Setup script
- `PRICING_MANAGEMENT.md` - Full documentation
- `PRICING_SETUP.md` - This file

### Updated Files:
- `.env` - Added AUDIO_PRICE_PER_MIN and VIDEO_PRICE_PER_MIN
- `apps/pricing/admin.py` - Enhanced admin display
- `webapp/views.py` - Uses database pricing
- All templates - Show prices from database

## How It Works

```
Request → get_active_pricing()
          ↓
       Database (Priority 1)
          ↓ (if not found)
       .env file (Priority 2)
          ↓ (if not found)
       Config defaults (Fallback)
```

## Verify Setup

**Check database:**
```bash
python django_admin/manage.py shell
```

```python
from apps.pricing.utils import get_active_pricing
print(get_active_pricing())
# Should show: {'audio_price_per_min': 500.0, 'video_price_per_min': 600.0}
```

**Check webapp:**
1. Go to `http://localhost:8000/`
2. Login
3. Dashboard should show: "500 UZS per minute (audio)"

**Check bot:**
1. Send audio to bot
2. Should show cost based on 500 sum/min

## Troubleshooting

**Prices not showing?**
```bash
# Run setup script again
python django_admin/scripts/create_default_pricing.py
```

**Can't access admin?**
```bash
# Create superuser
python django_admin/manage.py createsuperuser
```

**Database errors?**
```bash
# Run migrations
python django_admin/manage.py migrate
```

## Full Documentation

See `PRICING_MANAGEMENT.md` for:
- Complete guide
- Advanced features
- Multiple pricing plans
- Discounts
- Quality multipliers
- API reference

## Summary

✅ Prices: 500 sum (audio), 600 sum (video)
✅ Set in: Database (Django admin)
✅ Change: Django admin panel
✅ Effect: Immediate (no restart)
✅ Manage: `http://localhost:8000/admin/pricing/pricingplan/`

**Next:** Run the setup script! 🚀
