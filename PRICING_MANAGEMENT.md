# 💰 Pricing Management Guide

## Current Pricing

**Default Prices:**
- 🎵 Audio: **500 sum/min**
- 🎬 Video: **600 sum/min**

## Quick Start

### 1. Create Default Pricing Plan

Run this script to create the initial pricing plan in database:

```bash
python django_admin/scripts/create_default_pricing.py
```

You should see:
```
✅ Created default pricing plan!
  Name: Standard Plan
  Audio: 500 sum/min
  Video: 600 sum/min
  Status: Active
  Default: Yes
```

### 2. Change Prices in Admin

1. Go to Django admin: `http://localhost:8000/admin/`
2. Navigate to **Pricing Plans**
3. Click on **Standard Plan**
4. Update prices:
   - Audio Price per Minute: 500
   - Video Price per Minute: 600
5. Click **Save**

**Prices take effect immediately!** No restart needed.

## How It Works

### Priority System

Prices are loaded in this order:

1. **Database** (Django admin) - Highest priority
   - Active pricing plan with `is_default=True`
   - If not found, any active pricing plan

2. **.env file** - Medium priority
   - `AUDIO_PRICE_PER_MIN=500`
   - `VIDEO_PRICE_PER_MIN=600`

3. **Config defaults** - Fallback
   - Hardcoded in `bot/config.py`

### Where Prices Are Used

Pricing is read from database in these places:

**Webapp:**
- `webapp/views.py` - Upload, dashboard, transcriptions
- Uses `get_active_pricing()` function
- Calculates costs with `calculate_transcription_cost()`

**Bot Handlers:**
- `bot/handlers/media.py` - File transcription
- `bot/handlers/start.py` - Preview costs
- Falls back to config if database unavailable

## Managing Prices

### View Current Prices

**In Django Admin:**
```
http://localhost:8000/admin/pricing/pricingplan/
```

You'll see:
| Name | Audio Price | Video Price | Discount | Status | Is Default |
|------|-------------|-------------|----------|--------|------------|
| Standard Plan | **500** sum/min | **600** sum/min | No discount | ACTIVE | ✓ |

**In Code:**
```python
from apps.pricing.utils import get_active_pricing

pricing = get_active_pricing()
print(f"Audio: {pricing['audio_price_per_min']} sum/min")
print(f"Video: {pricing['video_price_per_min']} sum/min")
```

**In Shell:**
```bash
python django_admin/manage.py shell
>>> from apps.pricing.utils import get_active_pricing
>>> get_active_pricing()
{'audio_price_per_min': 500.0, 'video_price_per_min': 600.0}
```

### Change Prices

**Method 1: Django Admin** (Recommended)

1. Go to admin: `http://localhost:8000/admin/pricing/pricingplan/`
2. Click on pricing plan
3. Update prices
4. Click Save

✅ **Immediate effect** - No restart needed!

**Method 2: Update .env**

```bash
# Edit .env file
AUDIO_PRICE_PER_MIN=500
VIDEO_PRICE_PER_MIN=600
```

Then recreate pricing plan:
```bash
python django_admin/scripts/create_default_pricing.py
```

**Method 3: Django Shell**

```bash
python django_admin/manage.py shell
```

```python
from apps.pricing.models import PricingPlan

plan = PricingPlan.objects.get(is_default=True)
plan.audio_price_per_minute = 500
plan.video_price_per_minute = 600
plan.save()

print("✅ Prices updated!")
```

### Create New Pricing Plan

You can create multiple pricing plans for different scenarios:

**In Django Admin:**
1. Go to Pricing Plans
2. Click "Add Pricing Plan"
3. Fill in details:
   - Name: "Premium Plan"
   - Audio Price: 400 (cheaper)
   - Video Price: 500
   - Discount: 20% (optional)
4. Set as default if needed
5. Save

**In Code:**
```python
from apps.pricing.models import PricingPlan
from decimal import Decimal

plan = PricingPlan.objects.create(
    name="Premium Plan",
    description="Discounted plan for premium users",
    audio_price_per_minute=Decimal('400'),
    video_price_per_minute=Decimal('500'),
    discount_percentage=Decimal('20'),
    is_active=True,
    is_default=True  # Makes this the new default
)
```

## Advanced Features

### Discount Percentage

Apply a discount to all prices:

```
Original: 500 sum/min
Discount: 20%
Final: 400 sum/min
```

**In Admin:**
- Set "Discount Percentage" to 20
- Applies to both audio and video

### Quality Multipliers

Different quality levels have different costs:

```
Base Price: 500 sum/min

Fast Quality: 500 × 0.8 = 400 sum/min
Normal Quality: 500 × 1.0 = 500 sum/min
High Quality: 500 × 1.5 = 750 sum/min
```

**Configure in Admin:**
- Fast Quality Multiplier: 0.8
- Normal Quality Multiplier: 1.0
- High Quality Multiplier: 1.5

### Multiple Plans

Create different plans for different user types:

| Plan | Audio | Video | Discount | Users |
|------|-------|-------|----------|-------|
| Standard | 500 | 600 | 0% | Regular users |
| Premium | 400 | 500 | 20% | Paid subscribers |
| Business | 300 | 400 | 40% | Corporate clients |

**Set default plan:**
- Only one plan can be default
- Setting new default automatically unsets others
- Default plan is used for all users

## Database Structure

### PricingPlan Model

```python
class PricingPlan:
    name                        # Plan name
    description                 # Description
    audio_price_per_minute      # Audio price (sum/min)
    video_price_per_minute      # Video price (sum/min)
    discount_percentage         # Discount %
    fast_quality_multiplier     # Multiplier for fast
    normal_quality_multiplier   # Multiplier for normal
    high_quality_multiplier     # Multiplier for high
    max_duration_seconds        # Max duration
    max_file_size_mb           # Max file size
    is_active                   # Active status
    is_default                  # Default plan
    created_at                  # Created date
    updated_at                  # Updated date
```

### Files Structure

```
apps/pricing/
├── models.py              # PricingPlan model
├── admin.py               # Admin configuration
├── utils.py               # Pricing utilities
└── migrations/

django_admin/scripts/
└── create_default_pricing.py    # Setup script

webapp/views.py            # Uses get_active_pricing()
bot/handlers/media.py      # Uses pricing for calculations
```

## API Functions

### `get_active_pricing()`

Get current active pricing:

```python
from apps.pricing.utils import get_active_pricing

pricing = get_active_pricing()
# Returns: {'audio_price_per_min': 500.0, 'video_price_per_min': 600.0}
```

### `calculate_transcription_cost()`

Calculate cost for transcription:

```python
from apps.pricing.utils import calculate_transcription_cost

cost = calculate_transcription_cost('audio', 120, 'normal')
# Returns: Decimal('1000.00')  # 2 minutes × 500 sum/min
```

## Troubleshooting

### Prices not updating?

**Check 1:** Is pricing plan active?
```python
from apps.pricing.models import PricingPlan

plan = PricingPlan.objects.get(is_default=True)
print(f"Active: {plan.is_active}")
print(f"Audio: {plan.audio_price_per_minute}")
```

**Check 2:** Clear cache (if enabled)
```bash
python django_admin/manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
```

**Check 3:** Check logs
```bash
tail -f logs/django.log | grep "pricing"
```

### Multiple default plans?

Only one plan should be default. Fix:

```python
from apps.pricing.models import PricingPlan

# Set all to non-default
PricingPlan.objects.all().update(is_default=False)

# Set one as default
plan = PricingPlan.objects.get(name="Standard Plan")
plan.is_default = True
plan.save()
```

### Prices showing wrong in templates?

Make sure views pass pricing to templates:

```python
from apps.pricing.utils import get_active_pricing

def my_view(request):
    pricing = get_active_pricing()
    return render(request, 'template.html', {
        'settings': {
            'pricing': pricing
        }
    })
```

In template:
```django
{{ settings.pricing.audio_price_per_min }} sum/min
```

## Testing

### Test Price Changes

1. **Change prices in admin**
2. **Check in webapp:**
   - Go to dashboard
   - Prices should show new values

3. **Test transcription:**
   - Upload a file
   - Check calculated cost
   - Should use new prices

4. **Check bot:**
   - Send media to bot
   - Cost preview should show new prices

### Verify Database

```bash
python django_admin/manage.py shell
```

```python
from apps.pricing.models import PricingPlan

plan = PricingPlan.objects.get(is_default=True)
print(f"""
Current Pricing Plan: {plan.name}
Audio: {plan.audio_price_per_minute} sum/min
Video: {plan.video_price_per_minute} sum/min
Active: {plan.is_active}
Default: {plan.is_default}
""")
```

## Summary

✅ **Setup:** Run `python django_admin/scripts/create_default_pricing.py`
✅ **Manage:** Use Django admin at `/admin/pricing/pricingplan/`
✅ **Change prices:** Edit and save - takes effect immediately
✅ **No restart needed:** Prices read from database on each request

**Current Prices:**
- 🎵 Audio: **500 sum/min**
- 🎬 Video: **600 sum/min**

**Admin URL:**
`http://localhost:8000/admin/pricing/pricingplan/`

Done! 🎉
