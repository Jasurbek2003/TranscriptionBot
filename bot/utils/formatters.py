from typing import Union


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s" if secs > 0 else f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human-readable string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def format_currency(amount: Union[int, float], currency: str = "UZS") -> str:
    """
    Format amount with currency
    """
    return f"{amount:,.2f} {currency}"


def format_datetime(dt) -> str:
    """
    Format datetime to string
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_percentage(value: float, total: float) -> str:
    """
    Format percentage
    """
    if total == 0:
        return "0%"
    percentage = (value / total) * 100
    return f"{percentage:.1f}%"