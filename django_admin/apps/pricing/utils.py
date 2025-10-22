# django_admin/apps/pricing/utils.py
"""
Pricing utilities for getting current pricing from database
"""

import logging
from decimal import Decimal
from typing import Dict

logger = logging.getLogger(__name__)


def get_active_pricing() -> Dict[str, float]:
    """
    Get active pricing from database, fallback to config

    Returns:
        Dict with 'audio_price_per_min' and 'video_price_per_min'
    """
    from apps.pricing.models import PricingPlan
    from bot.config import settings

    try:
        # Try to get default/active pricing plan from database
        pricing_plan = PricingPlan.objects.filter(is_active=True, is_default=True).first()

        if pricing_plan:
            logger.debug(f"Using database pricing: {pricing_plan.name}")
            return {
                "audio_price_per_min": float(pricing_plan.audio_price_per_minute),
                "video_price_per_min": float(pricing_plan.video_price_per_minute),
            }

        # If no default plan, try to get any active plan
        pricing_plan = PricingPlan.objects.filter(is_active=True).first()

        if pricing_plan:
            logger.debug(f"Using active pricing plan: {pricing_plan.name}")
            return {
                "audio_price_per_min": float(pricing_plan.audio_price_per_minute),
                "video_price_per_min": float(pricing_plan.video_price_per_minute),
            }

    except Exception as e:
        logger.warning(f"Could not fetch pricing from database: {e}")

    # Fallback to config
    logger.debug("Using config pricing (fallback)")
    return {
        "audio_price_per_min": settings.pricing.audio_price_per_min,
        "video_price_per_min": settings.pricing.video_price_per_min,
    }


def calculate_transcription_cost(
        media_type: str, duration_seconds: int, quality: str = "normal"
) -> Decimal:
    """
    Calculate transcription cost

    Args:
        media_type: 'audio', 'voice', 'video', etc.
        duration_seconds: Duration in seconds
        quality: 'fast', 'normal', 'high'

    Returns:
        Cost in Decimal
    """
    from apps.pricing.models import PricingPlan

    try:
        # Try to get pricing plan from database
        pricing_plan = PricingPlan.objects.filter(is_active=True, is_default=True).first()

        if not pricing_plan:
            pricing_plan = PricingPlan.objects.filter(is_active=True).first()

        if pricing_plan:
            return Decimal(str(pricing_plan.calculate_price(media_type, duration_seconds, quality)))

    except Exception as e:
        logger.warning(f"Could not calculate cost from database: {e}")

    # Fallback to simple calculation from config
    pricing = get_active_pricing()
    duration_minutes = duration_seconds / 60  # Exact duration, not rounded

    if media_type in ["audio", "voice"]:
        cost = pricing["audio_price_per_min"] * duration_minutes
    else:
        cost = pricing["video_price_per_min"] * duration_minutes

    return Decimal(str(cost))


def get_pricing_for_templates():
    """
    Get pricing formatted for templates

    Returns:
        Dict with pricing info for templates
    """
    pricing = get_active_pricing()

    return {
        "audio_price_per_min": pricing["audio_price_per_min"],
        "video_price_per_min": pricing["video_price_per_min"],
    }
