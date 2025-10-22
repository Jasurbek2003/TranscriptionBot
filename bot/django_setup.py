"""
Django setup for bot

This module initializes Django settings so the bot can use Django ORM models.
Import this module before using any Django models in the bot.
"""

import os
import sys
from pathlib import Path

# Get project paths
BOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BOT_DIR.parent
DJANGO_DIR = PROJECT_ROOT / "django_admin"

# Add django_admin to Python path
sys.path.insert(0, str(DJANGO_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

# Setup Django
import django

django.setup()

from webapp.models import OneTimeToken

from apps.transactions.models import Transaction
from apps.transcriptions.models import Transcription

# Now Django models are available
from apps.users.models import TelegramUser
from apps.wallet.models import Wallet

__all__ = [
    "TelegramUser",
    "Wallet",
    "Transaction",
    "Transcription",
    "OneTimeToken",
]
