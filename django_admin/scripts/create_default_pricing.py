#!/usr/bin/env python
"""
Create default pricing plan in database
"""

import sys
import os
from pathlib import Path
from decimal import Decimal

# Add django_admin to path
sys.path.append(str(Path(__file__).parent.parent))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
django.setup()

from apps.pricing.models import PricingPlan
from bot.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_default_pricing():
    """Create default pricing plan"""

    # Check if default plan already exists
    existing_plan = PricingPlan.objects.filter(is_default=True).first()

    if existing_plan:
        logger.info(f"Default pricing plan already exists: {existing_plan.name}")
        logger.info(f"Audio: {existing_plan.audio_price_per_minute} sum/min")
        logger.info(f"Video: {existing_plan.video_price_per_minute} sum/min")

        # Ask if should update
        response = input("\nUpdate existing plan? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            logger.info("Skipping update")
            return existing_plan

        # Update existing plan
        existing_plan.audio_price_per_minute = Decimal(str(settings.pricing.audio_price_per_min))
        existing_plan.video_price_per_minute = Decimal(str(settings.pricing.video_price_per_min))
        existing_plan.save()

        logger.info(f"✅ Updated pricing plan: {existing_plan.name}")
        logger.info(f"  Audio: {existing_plan.audio_price_per_minute} sum/min")
        logger.info(f"  Video: {existing_plan.video_price_per_minute} sum/min")

        return existing_plan

    # Create new default plan
    plan = PricingPlan.objects.create(
        name="Standard Plan",
        description="Default pricing plan for all users",
        audio_price_per_minute=Decimal(str(settings.pricing.audio_price_per_min)),
        video_price_per_minute=Decimal(str(settings.pricing.video_price_per_min)),
        fast_quality_multiplier=Decimal('0.8'),
        normal_quality_multiplier=Decimal('1.0'),
        high_quality_multiplier=Decimal('1.5'),
        discount_percentage=Decimal('0'),
        max_duration_seconds=settings.ai.max_audio_duration_seconds,
        max_file_size_mb=settings.ai.max_file_size_mb,
        is_active=True,
        is_default=True
    )

    logger.info("✅ Created default pricing plan!")
    logger.info(f"  Name: {plan.name}")
    logger.info(f"  Audio: {plan.audio_price_per_minute} sum/min")
    logger.info(f"  Video: {plan.video_price_per_minute} sum/min")
    logger.info(f"  Status: {'Active' if plan.is_active else 'Inactive'}")
    logger.info(f"  Default: {'Yes' if plan.is_default else 'No'}")

    return plan


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Creating Default Pricing Plan")
    logger.info("=" * 60)
    logger.info(f"Audio Price: {settings.pricing.audio_price_per_min} sum/min")
    logger.info(f"Video Price: {settings.pricing.video_price_per_min} sum/min")
    logger.info("")

    try:
        plan = create_default_pricing()

        logger.info("\n" + "=" * 60)
        logger.info("✨ Success!")
        logger.info("=" * 60)
        logger.info("\nYou can now manage pricing from Django admin:")
        logger.info("  http://localhost:8000/admin/pricing/pricingplan/")
        logger.info("\nTo change prices:")
        logger.info("  1. Go to Django admin")
        logger.info("  2. Navigate to Pricing Plans")
        logger.info("  3. Edit the 'Standard Plan'")
        logger.info("  4. Update prices")
        logger.info("  5. Save")
        logger.info("\nPrices will be used immediately!")

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        sys.exit(1)
