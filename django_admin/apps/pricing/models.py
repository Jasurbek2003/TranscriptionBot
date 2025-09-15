from django.db import models
from django.utils.translation import gettext_lazy as _
from core.enums import MediaType, QualityLevel


class PricingPlan(models.Model):
    """Pricing plan model"""

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Plan Name")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )

    # Base prices per minute
    audio_price_per_minute = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Audio Price per Minute")
    )
    video_price_per_minute = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Video Price per Minute")
    )

    # Quality multipliers
    fast_quality_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.8,
        verbose_name=_("Fast Quality Multiplier")
    )
    normal_quality_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.0,
        verbose_name=_("Normal Quality Multiplier")
    )
    high_quality_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.5,
        verbose_name=_("High Quality Multiplier")
    )

    # Discounts
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_("Discount Percentage")
    )

    # Limits
    max_duration_seconds = models.IntegerField(
        default=3600,
        verbose_name=_("Max Duration (seconds)")
    )
    max_file_size_mb = models.IntegerField(
        default=50,
        verbose_name=_("Max File Size (MB)")
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active")
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_("Is Default Plan")
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )

    class Meta:
        db_table = 'pricing_plans'
        verbose_name = _("Pricing Plan")
        verbose_name_plural = _("Pricing Plans")
        ordering = ['name']

    def __str__(self):
        return self.name

    def calculate_price(self, media_type: str, duration_seconds: int, quality: str = 'normal'):
        """Calculate price for transcription"""
        duration_minutes = (duration_seconds + 59) // 60  # Round up

        # Get base price
        if media_type in ['audio', 'voice']:
            base_price = self.audio_price_per_minute
        else:
            base_price = self.video_price_per_minute

        # Apply quality multiplier
        if quality == 'fast':
            multiplier = self.fast_quality_multiplier
        elif quality == 'high':
            multiplier = self.high_quality_multiplier
        else:
            multiplier = self.normal_quality_multiplier

        # Calculate total
        total = base_price * duration_minutes * multiplier

        # Apply discount
        if self.discount_percentage > 0:
            total = total * (1 - self.discount_percentage / 100)

        return total

    def save(self, *args, **kwargs):
        """Ensure only one default plan"""
        if self.is_default:
            PricingPlan.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class Promotion(models.Model):
    """Promotion model"""

    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Promo Code")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )

    # Discount
    discount_type = models.CharField(
        max_length=20,
        choices=[
            ('percentage', 'Percentage'),
            ('fixed', 'Fixed Amount')
        ],
        verbose_name=_("Discount Type")
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Discount Value")
    )

    # Usage limits
    max_uses = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Max Total Uses")
    )
    max_uses_per_user = models.IntegerField(
        default=1,
        verbose_name=_("Max Uses per User")
    )
    current_uses = models.IntegerField(
        default=0,
        verbose_name=_("Current Uses")
    )

    # Validity
    valid_from = models.DateTimeField(
        verbose_name=_("Valid From")
    )
    valid_until = models.DateTimeField(
        verbose_name=_("Valid Until")
    )

    # Requirements
    minimum_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Minimum Amount")
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active")
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )

    class Meta:
        db_table = 'promotions'
        verbose_name = _("Promotion")
        verbose_name_plural = _("Promotions")
        ordering = ['-created_at']

    def __str__(self):
        return self.code

    def is_valid(self):
        """Check if promotion is valid"""
        from django.utils import timezone
        now = timezone.now()

        if not self.is_active:
            return False

        if now < self.valid_from or now > self.valid_until:
            return False

        if self.max_uses and self.current_uses >= self.max_uses:
            return False

        return True

    def calculate_discount(self, amount):
        """Calculate discount amount"""
        if self.discount_type == 'percentage':
            return amount * (self.discount_value / 100)
        else:
            return min(self.discount_value, amount)
