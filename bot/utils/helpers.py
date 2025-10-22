import asyncio
import logging
import os
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import aiofiles

logger = logging.getLogger(__name__)


async def download_file(bot, file_id: str, destination: Optional[Path] = None) -> Path:
    """
    Download file from Telegram
    """
    file = await bot.get_file(file_id)

    if destination is None:
        destination = Path(tempfile.mktemp())

    await bot.download_file(file.file_path, destination)
    return destination


async def extract_audio_from_video(
        video_path: Path, output_path: Optional[Path] = None
) -> Optional[Path]:
    """
    Extract audio from video using ffmpeg
    """
    if output_path is None:
        output_path = video_path.with_suffix(".mp3")

    try:
        # Run ffmpeg command
        cmd = [
            "ffmpeg",
            "-i",
            str(video_path),
            "-vn",  # No video
            "-acodec",
            "libmp3lame",  # MP3 codec
            "-ab",
            "128k",  # Bitrate
            "-ar",
            "44100",  # Sample rate
            "-y",  # Overwrite output
            str(output_path),
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode()}")
            return None

        return output_path

    except Exception as e:
        logger.error(f"Failed to extract audio: {e}")
        return None


async def save_file_from_bytes(data: bytes, filename: str, directory: Path) -> Path:
    """
    Save bytes data to file
    """
    filepath = directory / filename

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(data)

    return filepath


def get_file_extension(mime_type: str) -> str:
    """
    Get file extension from MIME type
    """
    mime_to_ext = {
        "audio/mpeg": "mp3",
        "audio/mp4": "m4a",
        "audio/ogg": "ogg",
        "audio/wav": "wav",
        "video/mp4": "mp4",
        "video/mpeg": "mpeg",
        "video/quicktime": "mov",
        "video/x-msvideo": "avi",
    }

    return mime_to_ext.get(mime_type, "bin")


def clean_filename(filename: str) -> str:
    """
    Clean filename from invalid characters
    """
    import re

    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', "", filename)
    # Limit length
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    return name + ext


def format_currency(amount: Decimal, currency: str = "UZS") -> str:
    """Format currency amount for display."""
    if currency == "UZS":
        # Format with thousands separator for UZS
        return f"{amount:,.0f} UZS"
    else:
        # Format with 2 decimal places for other currencies
        return f"{amount:.2f} {currency}"


def format_datetime(dt: datetime) -> str:
    """Format datetime for display."""
    from django.utils import timezone

    # Convert to local timezone if needed
    if dt.tzinfo is None:
        dt = timezone.make_aware(dt)

    now = timezone.now()

    # If today, show time only
    if dt.date() == now.date():
        return dt.strftime("Today %H:%M")

    # If yesterday, show "Yesterday"
    yesterday = now.date() - timezone.timedelta(days=1)
    if dt.date() == yesterday:
        return dt.strftime("Yesterday %H:%M")

    # If this year, show month and day
    if dt.year == now.year:
        return dt.strftime("%b %d, %H:%M")

    # Full date
    return dt.strftime("%b %d, %Y %H:%M")


def format_file_size(size_bytes: int) -> str:
    """Format file size for display."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.1f} GB"


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable format."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds == 0:
            return f"{minutes}m"
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes == 0:
            return f"{hours}h"
        return f"{hours}h {minutes}m"
