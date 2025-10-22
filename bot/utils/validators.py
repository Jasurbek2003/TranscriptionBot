import re
from typing import Optional


def validate_phone_number(phone: str) -> Optional[str]:
    """
    Validate and format phone number
    Returns formatted phone number or None if invalid
    """
    # Remove all non-digit characters
    phone = re.sub(r"\D", "", phone)

    # Check if it's a valid Uzbek phone number
    if re.match(r"^998\d{9}", phone):
        return f"+{phone}"
    elif re.match(r"^\d{9}", phone):
        return f"+998{phone}"

    return None


def validate_amount(amount: str) -> Optional[float]:
    """
    Validate amount string
    Returns float amount or None if invalid
    """
    try:
        amount = amount.replace(",", "").replace(" ", "")
        amount_float = float(amount)

        if amount_float <= 0:
            return None

        return amount_float
    except (ValueError, TypeError):
        return None


def validate_card_number(card: str) -> bool:
    """
    Validate card number using Luhn algorithm
    """
    card = re.sub(r"\D", "", card)

    if len(card) < 13 or len(card) > 19:
        return False

    # Luhn algorithm
    def luhn_checksum(card_number):
        def digits_of(n):
            return [int(d) for d in str(n)]

        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]

        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))

        return checksum % 10

    return luhn_checksum(card) == 0
