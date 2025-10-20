# django_admin/webapp/telegram_auth.py
"""
Telegram WebApp Authentication Utilities

This module provides utilities for validating and authenticating users
from Telegram WebApp (Mini App) using initData.
"""

import hmac
import hashlib
import json
import logging
from urllib.parse import parse_qsl
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


def validate_telegram_webapp_data(init_data: str, bot_token: str, max_age_seconds: int = 3600) -> Optional[Dict[str, Any]]:
    """
    Validate Telegram WebApp initData

    Args:
        init_data: The initData string from Telegram WebApp
        bot_token: Your bot token
        max_age_seconds: Maximum age of initData in seconds (default: 1 hour)

    Returns:
        Parsed and validated data dict, or None if validation fails

    Reference:
        https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        # Parse initData
        parsed_data = dict(parse_qsl(init_data))

        if not parsed_data:
            logger.warning("Empty initData received")
            return None

        # Check if hash exists
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            logger.warning("No hash in initData")
            return None

        # Check auth_date
        auth_date = parsed_data.get('auth_date')
        if not auth_date:
            logger.warning("No auth_date in initData")
            return None

        # Verify auth_date is not too old
        try:
            auth_timestamp = int(auth_date)
            auth_datetime = datetime.fromtimestamp(auth_timestamp)
            now = datetime.now()

            if (now - auth_datetime).total_seconds() > max_age_seconds:
                logger.warning(f"initData too old: {auth_datetime}")
                return None
        except (ValueError, OverflowError) as e:
            logger.warning(f"Invalid auth_date: {e}")
            return None

        # Create data check string
        # Sort keys alphabetically and create key=value string
        data_check_arr = [f"{k}={v}" for k, v in sorted(parsed_data.items())]
        data_check_string = '\n'.join(data_check_arr)

        # Calculate secret key
        # secret_key = HMAC_SHA256(<bot_token>, "WebAppData")
        secret_key = hmac.new(
            key="WebAppData".encode(),
            msg=bot_token.encode(),
            digestmod=hashlib.sha256
        ).digest()

        # Calculate hash
        # hash = HMAC_SHA256(<secret_key>, <data_check_string>)
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        # Compare hashes
        if calculated_hash != received_hash:
            logger.warning("Hash mismatch in initData validation")
            return None

        # Parse user data if present
        if 'user' in parsed_data:
            try:
                parsed_data['user'] = json.loads(parsed_data['user'])
            except json.JSONDecodeError:
                logger.warning("Failed to parse user data from initData")
                return None

        logger.info(f"Successfully validated Telegram WebApp data for user: {parsed_data.get('user', {}).get('id')}")
        return parsed_data

    except Exception as e:
        logger.error(f"Error validating Telegram WebApp data: {e}", exc_info=True)
        return None


def extract_user_from_init_data(validated_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract user information from validated initData

    Args:
        validated_data: Validated initData dict

    Returns:
        User data dict with keys: telegram_id, first_name, last_name, username, language_code
    """
    if not validated_data or 'user' not in validated_data:
        return None

    user_data = validated_data['user']

    return {
        'telegram_id': user_data.get('id'),
        'first_name': user_data.get('first_name', ''),
        'last_name': user_data.get('last_name', ''),
        'username': user_data.get('username', ''),
        'language_code': user_data.get('language_code', 'en'),
        'is_premium': user_data.get('is_premium', False),
    }


def create_telegram_auth_response(success: bool, message: str = "", user_data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Create a standardized response for Telegram auth endpoints

    Args:
        success: Whether authentication was successful
        message: Optional message
        user_data: Optional user data to include

    Returns:
        Response dict
    """
    response = {
        'success': success,
        'authenticated': success,
    }

    if message:
        response['message'] = message

    if user_data:
        response['user'] = user_data

    return response
